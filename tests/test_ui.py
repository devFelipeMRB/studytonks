from PySide6.QtWidgets import QPushButton, QTableWidget, QLineEdit
from PySide6.QtCore import QTimer
from app.ui.window import Window
from app.ui.widgets import Form


def fill_dialog(qapp, values):
    def fill():
        form = qapp.activeModalWidget()
        assert isinstance(form, Form)
        for key, value in values.items():
            widget = form.widgets[key]
            if hasattr(widget, "setText"):
                widget.setText(value)
            elif hasattr(widget, "setValue"):
                widget.setValue(value)
        form.accept()

    QTimer.singleShot(20, fill)


def test_empty_window_and_all_pages(service, qtbot):
    window = Window(service)
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    for row in range(9):
        window.nav.setCurrentRow(row)
    assert service.data["subjects"] == []
    window.quitting = True
    window.close()


def test_ui_end_to_end(service, qtbot, qapp):
    window = Window(service)
    qtbot.addWidget(window)
    window.show()
    fill_dialog(qapp, {"name": "Matemática Computacional"})
    window.new_subject()
    subject = service.data["subjects"][0]
    window.nav.setCurrentRow(3)
    fill_dialog(qapp, {"title": "Limites"})
    next(b for b in window.findChildren(QPushButton) if b.text() == "+ Sessão").click()
    fill_dialog(qapp, {"title": "Limites indeterminados"})
    next(
        b for b in window.findChildren(QPushButton) if b.text() == "+ Subsessão"
    ).click()
    window.nav.setCurrentRow(5)
    window.editor.setPlainText("Anotação com fórmula: \\frac{1}{x} 🦉")
    qtbot.waitUntil(lambda: bool(service.data["notes"]), timeout=3000)
    assert "Anotação" in next(iter(service.data["notes"].values()))["text"]
    window.nav.setCurrentRow(4)
    fill_dialog(qapp, {"name": "Primeira prova", "obtained": 18, "maximum": 20})
    window.new_assessment()
    assert service.history(subject["id"])[0]["percentage"] == 90
    window.nav.setCurrentRow(2)
    assert window.findChildren(QTableWidget) == [] or window.subject_id == subject["id"]
    window.nav.setCurrentRow(7)
    window.nav.setCurrentRow(0)
    search = next(
        w for w in window.findChildren(QLineEdit) if "Pesquisar" in w.placeholderText()
    )
    search.setText("MATEMÁTICA")
    window.quitting = True
    window.close()


def test_ui_edit_assessment_and_preferences(service, hierarchy, qtbot, qapp):
    s, _, _ = hierarchy
    a = service.assessment(s["id"], "Primeira", "2026-01-01", 18, 20)
    window = Window(service)
    qtbot.addWidget(window)
    window.show()
    window.subject_id = s["id"]
    fill_dialog(qapp, {"name": "Editada", "obtained": 15, "maximum": 20})
    window.new_assessment(a)
    assert (
        len(service.data["assessments"]) == 1
        and service.data["assessments"][0]["percentage"] == 75
    )
    service.settings(hours_format="clock")
    assert window.hours(5400) == "1 h 30 min"
    window.guard = lambda action: action()
    for page in range(9):
        window.nav.setCurrentRow(page)
    window.exit_app()


def test_pending_note_saved_on_navigation(service, hierarchy, qtbot):
    window = Window(service)
    qtbot.addWidget(window)
    window.subject_id = hierarchy[0]["id"]
    window.nav.setCurrentRow(5)
    window.editor.setPlainText("Texto antes do fechamento")
    window.nav.setCurrentRow(0)
    assert (
        "Texto antes do fechamento" in service.data["notes"][hierarchy[2]["id"]]["text"]
    )
    window.exit_app()


def test_ui_recovers_timer_paused(service, hierarchy, qtbot):
    from datetime import datetime

    service.save_active_study(
        {
            "subject_id": hierarchy[0]["id"],
            "session_id": hierarchy[1]["id"],
            "subsession_id": hierarchy[2]["id"],
        },
        90,
        datetime.now().isoformat(),
    )
    window = Window(service)
    qtbot.addWidget(window)
    assert window.timer.since is None and window.timer.seconds() == 90
    window.timer_end()
    assert service.data["study_logs"][0]["seconds"] == 90
    assert service.data["settings"]["active_study"] is None
    window.exit_app()


def test_ui_bootcamp_reminder_and_manual_time(service, hierarchy, qtbot, qapp):
    window = Window(service)
    qtbot.addWidget(window)
    window.subject_id = hierarchy[0]["id"]
    window.show()
    window.nav.setCurrentRow(2)
    fill_dialog(qapp, {"name": "Semana de reforço", "hours": 24})
    window.edit_bootcamp(None)
    assert service.data["bootcamps"][0]["hours"] == 24
    window.nav.setCurrentRow(6)
    fill_dialog(qapp, {"title": "Revisar limites"})
    window.edit_reminder(None)
    assert service.data["reminders"][0]["title"] == "Revisar limites"
    window.nav.setCurrentRow(7)
    fill_dialog(qapp, {})
    window.manual_time()
    assert service.data["study_logs"][0]["seconds"] == 3600
    window.exit_app()
