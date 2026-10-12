"""Regressions for persistence boundaries and time-sensitive study workflows."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
import zipfile

import pytest

from app.services.reminders import occurrence
from app.services.study import metrics
from app.storage.schema import StorageError
from app.storage.store import Store


def test_returned_entity_cannot_modify_saved_snapshot(service):
    subject = service.subject("Python")
    subject["name"] = "Alterado sem salvar"
    subject["target"] = -1

    assert service.data["subjects"][0]["name"] == "Python"
    assert json.loads(service.store.path.read_text())["subjects"] == service.data["subjects"]
    # A subsequent transaction must still accept the intact saved entity.
    service.subject("Matemática")


def test_commit_does_not_keep_callers_nested_references(service):
    candidate = copy.deepcopy(service.data)
    service.store.commit(candidate)
    candidate["settings"]["theme"] = "dark"
    candidate["subjects"].append({"invalid": True})

    assert service.data["settings"]["theme"] == "automatic"
    assert service.data["subjects"] == []


def test_previous_snapshot_survives_interrupted_replacement(service, hierarchy, monkeypatch):
    previous = service.store.root / "state.previous.json"
    original_previous = previous.read_bytes()
    original_state = service.store.path.read_bytes()
    import app.storage.store as storage_module

    replace = storage_module.os.replace

    def fail_previous(source, destination):
        if Path(destination) == previous:
            raise OSError("Interrupted recovery snapshot replacement")
        return replace(source, destination)

    monkeypatch.setattr(storage_module.os, "replace", fail_previous)
    with pytest.raises(OSError):
        service.subject("Transação interrompida")

    assert previous.read_bytes() == original_previous
    assert service.store.path.read_bytes() == original_state
    assert len(service.data["subjects"]) == 1
    assert not list(service.store.root.glob("*.tmp"))


def test_closed_store_cannot_write_after_another_instance_acquires_lock(service):
    root = service.store.root
    service.store.close()
    replacement = Store(root)
    try:
        original = replacement.path.read_bytes()
        with pytest.raises(StorageError):
            service.subject("Escritor antigo")
        assert replacement.path.read_bytes() == original
    finally:
        replacement.close()


def test_backup_creates_selected_destination_directory(service, hierarchy, tmp_path):
    destination = tmp_path / "exports" / "studytonks" / "backup.zip"
    assert service.store.backup(destination) == destination
    assert Store.inspect_backup(destination) == service.data


def test_missing_backup_is_reported_without_changing_data(service, tmp_path):
    original = service.store.path.read_bytes()
    with pytest.raises(StorageError):
        service.store.restore(tmp_path / "missing.zip")
    assert service.store.path.read_bytes() == original


def test_missing_schema_marker_can_recover_previous_valid_snapshot(service, hierarchy):
    root = service.store.root
    expected = json.loads((root / "state.previous.json").read_text())
    corrupted = copy.deepcopy(service.data)
    del corrupted["schema_version"]
    original = json.dumps(corrupted)
    service.store.close()
    (root / "state.json").write_text(original, encoding="utf-8")

    reopened = Store(root)
    try:
        assert reopened.recovered
        assert reopened.data == expected
        assert next(root.glob("corrupt-*.json")).read_text(encoding="utf-8") == original
    finally:
        reopened.close()


def test_invalid_schema_marker_in_backup_is_rejected(service, tmp_path):
    candidate = copy.deepcopy(service.data)
    del candidate["schema_version"]
    archive_path = tmp_path / "invalid.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("state.json", json.dumps(candidate))

    original = service.store.path.read_bytes()
    with pytest.raises(StorageError):
        service.store.restore(archive_path)
    assert service.store.path.read_bytes() == original


@pytest.mark.parametrize("key", ["settings", "notes"])
def test_invalid_legacy_backup_cannot_replace_current_data(service, tmp_path, key):
    candidate = copy.deepcopy(service.data)
    candidate["schema_version"] = 0
    candidate[key] = None
    archive_path = tmp_path / "broken-legacy.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("state.json", json.dumps(candidate))

    original = service.store.path.read_bytes()
    with pytest.raises(StorageError):
        service.store.restore(archive_path)
    assert service.store.path.read_bytes() == original


def test_orphan_reminder_link_is_rejected(service, hierarchy):
    with pytest.raises(StorageError):
        service.add(
            "reminders",
            title="Estudar",
            when="2026-01-05T08:00:00",
            recurrence="once",
            days=[],
            enabled=True,
            subject_id=None,
            session_id=hierarchy[1]["id"],
        )
    assert service.data["reminders"] == []


def test_same_day_assessments_follow_entry_time_instead_of_random_uuid(service, hierarchy):
    subject = hierarchy[0]
    first = service.assessment(subject["id"], "Primeira", "2026-01-05", 50, 100)
    second = service.assessment(subject["id"], "Segunda", "2026-01-05", 90, 100)
    service.update(
        "assessments",
        first["id"],
        id="ffffffff-ffff-4fff-8fff-ffffffffffff",
        created_at="2026-01-05T08:00:00",
    )
    service.update(
        "assessments",
        second["id"],
        id="00000000-0000-4000-8000-000000000000",
        created_at="2026-01-05T09:00:00",
    )

    history = service.history(subject["id"])
    assert [row["name"] for row in history] == ["Primeira", "Segunda"]
    assert metrics(list(reversed(history)))["trend"] == 40
    assert metrics(history)["last"] == 90


def test_composite_assessment_never_invents_result_for_unassessed_subsession(service, hierarchy):
    subject, session, sub = hierarchy
    other = service.subsession(subject["id"], session["id"], "Não avaliada")
    service.assessment(
        subject["id"],
        "Prova composta",
        "2026-01-05",
        components=[{"subsession_id": sub["id"], "obtained": 9, "maximum": 10}],
        subsession_id=other["id"],
    )

    assert service.history(subject["id"], other["id"]) == []
    assert len(service.history(subject["id"])) == 1
    assert service.history(subject["id"], sub["id"])[0]["percentage"] == 90


@pytest.mark.parametrize("recurrence,days", [("daily", []), ("weekly", [0])])
def test_recurring_reminder_preserves_exact_scheduled_time(recurrence, days):
    reminder = {
        "when": "2026-01-05T08:00:45.500000",
        "recurrence": recurrence,
        "days": days,
        "enabled": True,
    }
    assert occurrence(reminder, datetime(2026, 1, 5, 8, 0, 30)) is None
    now = datetime(2026, 1, 5, 8, 0, 46)
    token = occurrence(reminder, now)
    assert token == reminder["when"]
    reminder["last_fired"] = token
    assert occurrence(reminder, now + timedelta(seconds=1)) is None


def test_manual_log_without_dates_records_actual_interval(service, hierarchy):
    log = service.log(hierarchy[0]["id"], 1800)
    duration = datetime.fromisoformat(log["end"]) - datetime.fromisoformat(log["start"])
    assert duration.total_seconds() == 1800
    assert log["date"] == log["start"][:10]


def test_log_with_only_end_derives_start(service, hierarchy):
    log = service.log(hierarchy[0]["id"], 900, end="2026-01-06T00:05:00")
    assert log["start"] == "2026-01-05T23:50:00"
    assert log["date"] == "2026-01-05"


def test_log_validates_real_chronology_for_different_iso_separators(service, hierarchy):
    log = service.log(
        hierarchy[0]["id"],
        3600,
        start="2026-01-05T08:00:00",
        end="2026-01-05 09:00:00",
    )
    assert log["seconds"] == 3600

    with pytest.raises(StorageError):
        service.log(
            hierarchy[0]["id"],
            3600,
            start="2026-01-05 09:00:00",
            end="2026-01-05T08:00:00",
        )
    assert len(service.data["study_logs"]) == 1
