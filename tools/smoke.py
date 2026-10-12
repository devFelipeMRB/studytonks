"""Open the real desktop for every page using isolated data, then exit."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app.storage.store import Store
from app.services.study import StudyService
from app.ui.window import Window

app = QApplication([])
with tempfile.TemporaryDirectory(prefix="studytonks-smoke-") as folder:
    store = Store(folder)
    service = StudyService(store)
    subject = service.subject("Validação temporária")
    session = service.session(subject["id"], "Sessão")
    sub = service.subsession(subject["id"], session["id"], "Subsessão")
    service.assessment(
        subject["id"],
        "Avaliação temporária",
        "2026-01-01",
        18,
        20,
        subsession_id=sub["id"],
    )
    window = Window(service)
    # Exceptions must fail this check instead of opening a blocking message box.
    window.guard = lambda action: action()
    window.show()
    for page in range(9):
        window.nav.setCurrentRow(page)
    assert window.isVisible()
    QTimer.singleShot(300, window.exit_app)
    result = app.exec()
    store.close()
    if result:
        sys.exit(result)
print("Interface aberta; nove páginas renderizadas; dados temporários descartados.")
