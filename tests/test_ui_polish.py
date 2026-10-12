from PySide6.QtWidgets import QMessageBox
from app.ui.window import Window


def test_failed_note_save_preserves_editor_and_navigation(
    service, hierarchy, qtbot, monkeypatch
):
    window = Window(service)
    qtbot.addWidget(window)
    window.subject_id = hierarchy[0]["id"]
    window.nav.setCurrentRow(5)
    window.editor.setPlainText("Texto que não pode desaparecer")
    original = service.note

    def fail(*args):
        raise OSError("Disco indisponível")

    monkeypatch.setattr(service, "note", fail)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window.nav.setCurrentRow(0)
    assert window.nav.currentRow() == 5 and window.stack.currentIndex() == 5
    assert window.editor.toPlainText() == "Texto que não pode desaparecer"
    assert window.note_dirty and len(warnings) == 1
    monkeypatch.setattr(service, "note", original)
    window.nav.setCurrentRow(0)
    assert (
        "Texto que não pode desaparecer"
        in service.data["notes"][hierarchy[2]["id"]]["text"]
    )
    window.exit_app()


def test_failed_note_save_preserves_subject_selection(
    service, hierarchy, qtbot, monkeypatch
):
    second = service.subject("Segunda matéria")
    window = Window(service)
    qtbot.addWidget(window)
    window.subject_id = hierarchy[0]["id"]
    window.nav.setCurrentRow(5)
    window.editor.setPlainText("Não salvo")
    original = service.note

    def fail(*args):
        raise OSError("Disco indisponível")

    monkeypatch.setattr(service, "note", fail)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)
    window.guard(lambda: window.choose_subject(second["id"]))
    assert window.subject_id == hierarchy[0]["id"]
    assert window.editor.toPlainText() == "Não salvo"
    monkeypatch.setattr(service, "note", original)
    window.exit_app()
