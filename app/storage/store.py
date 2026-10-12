"""Versioned, atomic JSON storage. One writer per data directory.

Schema 1 uses a transactional state.json for cross-entity consistency; notes
are HTML strings in the same snapshot. Backups contain validated JSON only.
"""

from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
from datetime import datetime
from PySide6.QtCore import QLockFile

from app.storage.schema import (
    StorageError,
    defaults,
    validate,
    migrate,
    RecoveryRequired,
    UnsupportedSchema,
)


def data_directory() -> Path:
    return Path(
        os.environ.get("STUDYTONKS_DATA_DIR")
        or (
            Path(os.environ.get("APPDATA", Path.home() / ".local/share")) / "Studytonks"
        )
    )


class Store:
    def __init__(self, root=None, recovery_source=None):
        self.root = Path(root or data_directory())
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "backups").mkdir(exist_ok=True)
        (self.root / "logs").mkdir(exist_ok=True)
        self.lock = QLockFile(str(self.root / ".writer.lock"))
        self.lock.setStaleLockTime(0)
        if not self.lock.tryLock(100):
            raise StorageError("Studytonks já está aberto nesta pasta de dados.")
        self.path = self.root / "state.json"
        self._closed = False
        self.recovered = False
        try:
            try:
                self.data = self._load()
            except RecoveryRequired:
                if recovery_source is None:
                    raise
                candidate = self.inspect_backup(recovery_source)
                shutil.copy2(
                    self.path,
                    self.root / f"corrupt-{datetime.now():%Y%m%d%H%M%S%f}.json",
                )
                self._atomic(candidate)
                self.data = candidate
                self.recovered = True
        except Exception:
            self.lock.unlock()
            raise

    def _load(self):
        if not self.path.exists():
            data = defaults()
            self._atomic(data)
            return data
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            old_version = raw.get("schema_version") if isinstance(raw, dict) else None
            data = migrate(raw)
            if old_version == 0:
                shutil.copy2(self.path, self.root / "state.pre-migration.json")
                self._atomic(data)
            return data
        except UnsupportedSchema:
            raise
        except (ValueError, TypeError, KeyError, StorageError):
            previous = self.root / "state.previous.json"
            try:
                recovered = validate(json.loads(previous.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError, KeyError, StorageError) as exc:
                raise RecoveryRequired(
                    "Dados corrompidos. Original preservado; restaure um backup válido."
                ) from exc
            shutil.copy2(
                self.path, self.root / f"corrupt-{datetime.now():%Y%m%d%H%M%S%f}.json"
            )
            self._atomic(recovered)
            self.recovered = True
            return recovered

    def _atomic(self, data):
        self._atomic_json(self.path, data)

    def _atomic_json(self, destination, data):
        fd, name = tempfile.mkstemp(dir=self.root, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, destination)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def commit(self, candidate):
        self._require_open()
        # Callers may retain the candidate or an entity returned by a service.
        # A persisted snapshot must not change when those objects are edited.
        candidate = copy.deepcopy(candidate)
        validate(candidate)
        interval = candidate["settings"].get("backup_days", 1)
        directory = Path(
            candidate["settings"].get("backup_dir") or self.root / "backups"
        )
        if interval > 0:
            existing = (
                sorted(directory.glob("auto-*.zip")) if directory.exists() else []
            )
            if (
                not existing
                or (datetime.now().timestamp() - existing[-1].stat().st_mtime)
                >= interval * 86400
            ):
                directory.mkdir(parents=True, exist_ok=True)
                self.backup(
                    directory / f"auto-{datetime.now():%Y%m%d-%H%M%S%f}.zip", candidate
                )
                for old in sorted(directory.glob("auto-*.zip"))[:-30]:
                    old.unlink()
        if self.path.exists():
            self._atomic_json(self.root / "state.previous.json", self.data)
        self._atomic(candidate)
        self.data = candidate

    def backup(self, destination=None, payload=None):
        self._require_open()
        destination = Path(
            destination
            or self.root / "backups" / f"manual-{datetime.now():%Y%m%d-%H%M%S%f}.zip"
        )
        payload = self.data if payload is None else payload
        validate(payload)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=destination.parent, suffix=".zip.tmp")
        os.close(fd)
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "state.json",
                    json.dumps(payload, ensure_ascii=False, allow_nan=False),
                )
            with open(temporary, "rb") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return destination

    @staticmethod
    def inspect_backup(source):
        try:
            with zipfile.ZipFile(source) as archive:
                entries = archive.infolist()
                if (
                    len(entries) != 1
                    or entries[0].filename != "state.json"
                    or entries[0].file_size > 50_000_000
                ):
                    raise StorageError("Backup inválido ou caminhos inseguros.")
                with archive.open("state.json") as stream:
                    raw = stream.read(50_000_001)
                if len(raw) > 50_000_000:
                    raise StorageError("Backup muito grande.")
                return migrate(json.loads(raw))
        except StorageError:
            raise
        except (
            zipfile.BadZipFile,
            RuntimeError,
            ValueError,
            UnicodeError,
            OSError,
            NotImplementedError,
        ) as exc:
            raise StorageError(
                "ZIP inválido, danificado ou protegido por senha. Os dados atuais foram preservados."
            ) from exc

    def restore(self, source):
        self._require_open()
        candidate = self.inspect_backup(source)
        self.backup()
        self.commit(candidate)

    def close(self):
        if not self._closed:
            self.lock.unlock()
            self._closed = True

    def _require_open(self):
        if self._closed:
            raise StorageError("A pasta de dados já foi fechada. Abra o Studytonks novamente.")
