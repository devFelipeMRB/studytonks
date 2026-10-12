"""Studytonks desktop entry point; works offline, including frozen distributions."""

import sys
import logging
import tempfile
from PySide6.QtCore import QTimer
from logging.handlers import RotatingFileHandler
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QFileDialog
from app.storage.store import Store, StorageError, RecoveryRequired
from app.services.study import StudyService
from app.ui.window import Window


def run(root=None, smoke=False):
    app = QApplication(sys.argv)
    app.setApplicationName("Studytonks")
    app.setOrganizationName("Studytonks")
    try:
        store = Store(root)
    except RecoveryRequired as exc:
        response = QMessageBox.question(
            None,
            "Recuperar dados",
            str(exc)
            + "\nSelecionar um backup ZIP para restaurar? O original será preservado.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response != QMessageBox.Yes:
            return 1
        source, _ = QFileDialog.getOpenFileName(
            None, "Selecionar backup válido", "", "ZIP (*.zip)"
        )
        if not source:
            return 1
        try:
            store = Store(root, recovery_source=source)
        except (StorageError, OSError, ValueError) as failure:
            QMessageBox.critical(None, "Recuperação não concluída", str(failure))
            return 1
    except (StorageError, OSError) as exc:
        QMessageBox.critical(None, "Studytonks", str(exc))
        return 1
    handler = RotatingFileHandler(
        store.root / "logs" / "app.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger("studytonks").addHandler(handler)
    service = StudyService(store)
    if smoke:
        subject = service.subject("Validação temporária")
        session = service.session(subject["id"], "Sessão temporária")
        sub = service.subsession(subject["id"], session["id"], "Subsessão temporária")
        service.note(sub["id"], "<p>Teste isolado de persistência</p>")
        assessment = service.assessment(
            subject["id"],
            "Prova temporária",
            "2026-01-01",
            18,
            20,
            subsession_id=sub["id"],
        )
        service.log(subject["id"], 60, sub["id"])
        assert assessment["percentage"] == 90
        assert len(service.history(subject["id"])) == 1
    window = Window(service)
    if smoke:
        window.guard = lambda action: action()
        for page in range(9):
            window.nav.setCurrentRow(page)
        QTimer.singleShot(300, window.exit_app)
    if store.data["settings"]["minimized"] and QSystemTrayIcon.isSystemTrayAvailable():
        window.hide()
    else:
        window.show()
    app.aboutToQuit.connect(store.close)
    result = app.exec()
    handler.close()
    logging.getLogger("studytonks").removeHandler(handler)
    return result


def main():
    if "--smoke-test" in sys.argv:
        with tempfile.TemporaryDirectory(prefix="studytonks-packaged-smoke-") as root:
            return run(root, smoke=True)
    return run()


if __name__ == "__main__":
    sys.exit(main())
