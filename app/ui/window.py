from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QMessageBox,
    QSystemTrayIcon,
    QMenu,
    QScrollArea,
    QHeaderView,
)
from app.ui.widgets import Form
from app.ui.theme import stylesheet


def fmt(value):
    return "—" if value is None else f"{value:.1f}%"


from app.ui.pages.subjects import SubjectPages
from app.ui.pages.notes import NotePages
from app.ui.pages.assessments import AssessmentPages
from app.ui.pages.study import StudyPages
from app.ui.pages.agenda import AgendaPages
from app.ui.pages.settings import SettingsPages


class Window(
    SubjectPages,
    NotePages,
    AssessmentPages,
    StudyPages,
    AgendaPages,
    SettingsPages,
    QMainWindow,
):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.subject_id = None
        self.note_id = None
        self.timer = None
        self.timer_link = None
        self.restore_active_timer()
        self.quitting = False
        self.setWindowTitle("Studytonks · Learn. Track. Master.")
        self.resize(1240, 820)
        self.setMinimumSize(850, 600)
        self.icon = QIcon(str(Path(__file__).parents[1] / "assets" / "studytonks.ico"))
        self.setWindowIcon(self.icon)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(238)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(16, 26, 16, 18)
        brand_row = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(
            QPixmap(
                str(Path(__file__).parents[1] / "assets" / "studytonks.png")
            ).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        brand = QLabel("Studytonks")
        brand.setObjectName("brand")
        brand_row.addWidget(mark)
        brand_row.addWidget(brand)
        brand_row.addStretch()
        sl.addLayout(brand_row)
        tagline = QLabel("Learn. Track. Master.")
        tagline.setObjectName("tagline")
        sl.addWidget(tagline)
        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setIconSize(QSize(18, 18))
        self.nav.addItems(
            [
                "Dashboard",
                "Matérias",
                "Detalhes da matéria",
                "Sessões e submatérias",
                "Avaliações",
                "Anotações",
                "Agenda e lembretes",
                "Estatísticas",
                "Configurações",
            ]
        )
        sl.addWidget(self.nav)
        footer = QLabel("Seu aprendizado, no seu ritmo.")
        footer.setObjectName("muted")
        footer.setWordWrap(True)
        sl.addWidget(footer)
        layout.addWidget(side)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.pages = []
        for _ in range(9):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            page = QWidget()
            box = QVBoxLayout(page)
            box.setContentsMargins(32, 28, 32, 24)
            box.setSpacing(16)
            scroll.setWidget(page)
            self.stack.addWidget(scroll)
            self.pages.append((page, box))
        self.nav.currentRowChanged.connect(
            lambda row: self.guard(lambda: self.navigate(row))
        )
        self.note_save = QTimer(self)
        self.note_save.setSingleShot(True)
        self.note_save.setInterval(600)
        self.note_save.timeout.connect(lambda: self.guard(self.save_note))
        self.tray = QSystemTrayIcon(self.icon, self)
        menu = QMenu()
        menu.addAction("Abrir Studytonks", self.show_normal)
        self.next_action = menu.addAction(
            "Próximo lembrete", lambda: self.nav.setCurrentRow(6)
        )
        menu.addAction("Iniciar sessão de estudo", self.timer_start)
        menu.addAction("Configurações", lambda: self.nav.setCurrentRow(8))
        menu.addSeparator()
        menu.addAction("Sair completamente", self.exit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: (
                self.show_normal() if reason == QSystemTrayIcon.Trigger else None
            )
        )
        self.tray.messageClicked.connect(self.show_normal)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.ticker = QTimer(self)
        self.ticker.setInterval(1000)
        self.ticker.timeout.connect(self.tick)
        self.ticker.start()
        self.apply_theme()
        self.nav.setCurrentRow(0)
        QApplication.styleHints().colorSchemeChanged.connect(
            lambda _: self.apply_theme()
        )
        if service.store.recovered:
            QTimer.singleShot(
                0,
                lambda: QMessageBox.warning(
                    self,
                    "Recuperação de dados",
                    "O arquivo corrompido foi preservado e a última cópia válida foi recuperada. Confira seus dados.",
                ),
            )

    def guard(self, action):
        try:
            return action()
        except Exception as exc:
            import logging

            logging.getLogger("studytonks").error(
                "Operation failed: %s", type(exc).__name__
            )
            QMessageBox.warning(self, "Não foi possível concluir", str(exc))
            return None

    def button(self, layout, text, action):
        button = QPushButton(text)
        button.clicked.connect(lambda: self.guard(action))
        layout.addWidget(button)
        return button

    def title(self, layout, text, subtitle=""):
        label = QLabel(text)
        label.setObjectName("heading")
        layout.addWidget(label)
        if subtitle:
            layout.addWidget(QLabel(subtitle))

    def clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear(item.layout())

    def navigate(self, row):
        try:
            self.save_note()
        except Exception:
            self.nav.blockSignals(True)
            self.nav.setCurrentRow(self.stack.currentIndex())
            self.nav.blockSignals(False)
            raise
        self.note_id = None
        self.stack.setCurrentIndex(row)
        box = self.pages[row][1]
        self.clear(box)
        builders = [
            self.dashboard,
            self.subjects_page,
            self.details,
            self.structure,
            self.assessments_page,
            self.notes_page,
            self.agenda,
            self.statistics,
            self.settings_page,
        ]
        self.guard(lambda: builders[row](box))

    def refresh(self):
        self.navigate(self.nav.currentRow())

    def subject(self):
        return next(
            (s for s in self.service.data["subjects"] if s["id"] == self.subject_id),
            None,
        )

    def subject_choices(self):
        return [
            (s["name"] + (" (arquivada)" if s["archived"] else ""), s["id"])
            for s in self.service.data["subjects"]
        ]

    def selector(self, box):
        choices = self.subject_choices()
        if not choices:
            box.addWidget(QLabel("Crie sua primeira matéria para começar."))
            self.button(box, "+ Nova matéria", self.new_subject)
            return False
        if self.subject() is None:
            self.subject_id = choices[0][1]
        combo = QComboBox()
        for name, identifier in choices:
            combo.addItem(name, identifier)
        combo.setCurrentIndex(combo.findData(self.subject_id))
        combo.currentIndexChanged.connect(
            lambda: self.guard(lambda: self.choose_subject(combo.currentData(), combo))
        )
        box.addWidget(combo)
        return True

    def choose_subject(self, identifier, combo=None):
        try:
            self.save_note()
        except Exception:
            if combo is not None:
                combo.blockSignals(True)
                combo.setCurrentIndex(combo.findData(self.subject_id))
                combo.blockSignals(False)
            raise
        self.subject_id = identifier
        self.refresh()

    def show_normal(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def apply_theme(self):
        setting = self.service.data["settings"]["theme"]
        self.dark = setting == "dark" or (
            setting == "automatic"
            and QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        )
        self.setStyleSheet(stylesheet(self.dark))

    def hours(self, seconds):
        if self.service.data["settings"]["hours_format"] == "clock":
            minutes = round(seconds / 60)
            return f"{minutes // 60} h {minutes % 60:02} min"
        return f"{seconds / 3600:.1f} h"

    def table(self, box, headers, rows):
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(44)
        table.setShowGrid(False)
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                table.setItem(i, j, QTableWidgetItem(str(value)))
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.resizeColumnsToContents()
        table.setMinimumHeight(210)
        box.addWidget(table)
        return table

    def selected(self, table, items):
        row = table.currentRow()
        if row < 0:
            raise ValueError("Selecione um item primeiro.")
        return items[row]

    def dialog(self, title, fields, callback):
        form = Form(self, title, fields)
        form.on_submit = callback
        if form.exec() == Form.Accepted:
            self.refresh()
            return form.result_value

    def confirm(self, text):
        return (
            QMessageBox.question(
                self,
                "Confirmar operação",
                text,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            == QMessageBox.Yes
        )

    def exit_app(self):
        if self.timer:
            if not self.confirm("Encerrar e salvar a sessão de estudo antes de sair?"):
                return
            self.guard(self.timer_end)
            if self.timer:
                return
        try:
            self.save_note()
        except Exception as exc:
            QMessageBox.warning(self, "Anotação não salva", str(exc))
            return
        self.quitting = True
        self.close()

    def closeEvent(self, event):
        try:
            self.save_note()
        except Exception as exc:
            QMessageBox.warning(self, "Anotação não salva", str(exc))
            event.ignore()
            return
        if (
            not self.quitting
            and self.service.data["settings"]["background"]
            and QSystemTrayIcon.isSystemTrayAvailable()
        ):
            if not self.service.data["settings"].get("tray_explained"):
                QMessageBox.information(
                    self,
                    "Studytonks continua aberto",
                    "A janela será ocultada. Os lembretes continuam ativos. Use “Sair completamente” na bandeja para encerrar.",
                )
                self.service.settings(tray_explained=True)
            self.hide()
            event.ignore()
            return
        if self.timer:
            if not self.confirm("Salvar e encerrar a sessão de estudo?"):
                event.ignore()
                return
            self.guard(self.timer_end)
            if self.timer:
                event.ignore()
                return
        self.ticker.stop()
        self.tray.hide()
        self.service.store.close()
        event.accept()
