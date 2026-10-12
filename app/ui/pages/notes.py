from __future__ import annotations
from datetime import datetime
from PySide6.QtGui import QTextCharFormat, QFont, QTextListFormat
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QTextEdit,
)


def fmt(value):
    return "—" if value is None else f"{value:.1f}%"


class NotePages:
    def notes_page(self, box):
        self.title(
            box,
            "Anotações",
            "Seu conhecimento, preservado automaticamente. Fórmulas LaTeX são mantidas como texto.",
        )
        if not self.selector(box):
            return
        subs = [
            s
            for s in self.service.data["subsessions"]
            if s["subject_id"] == self.subject_id
        ]
        if not subs:
            box.addWidget(QLabel("Crie uma subsessão na área Sessões para escrever."))
            return
        combo = QComboBox()
        for s in subs:
            combo.addItem(s["title"], s["id"])
        preferred = getattr(self, "preferred_sub", None)
        if combo.findData(preferred) >= 0:
            combo.setCurrentIndex(combo.findData(preferred))
        box.addWidget(combo)
        tools = QHBoxLayout()
        box.addLayout(tools)
        self.editor = QTextEdit()
        self.editor.setMinimumHeight(280)
        self.note_status = QLabel()
        box.addWidget(self.note_status)

        def charformat(bold=False, italic=False, heading=False, code=False):
            f = QTextCharFormat()
            if bold:
                f.setFontWeight(
                    QFont.Normal
                    if self.editor.fontWeight() == QFont.Bold
                    else QFont.Bold
                )
            if italic:
                f.setFontItalic(not self.editor.fontItalic())
            if heading:
                f.setFontPointSize(20)
                f.setFontWeight(QFont.Bold)
            if code:
                f.setFontFamilies(["Consolas"])
                f.setFontPointSize(11)
            self.editor.mergeCurrentCharFormat(f)
            self.editor.setFocus()

        self.button(tools, "Título", lambda: charformat(heading=True))
        self.button(tools, "Negrito", lambda: charformat(bold=True))
        self.button(tools, "Itálico", lambda: charformat(italic=True))
        self.button(tools, "Código", lambda: charformat(code=True))

        def listing():
            f = QTextListFormat()
            f.setStyle(QTextListFormat.ListDisc)
            self.editor.textCursor().createList(f)

        self.button(tools, "Lista", listing)
        self.button(
            tools,
            "Parágrafo",
            lambda: self.editor.setCurrentCharFormat(QTextCharFormat()),
        )
        box.addWidget(self.editor)
        chart_holder = QWidget()
        ch = QVBoxLayout(chart_holder)
        box.addWidget(chart_holder)

        def load():
            try:
                self.save_note()
            except Exception:
                combo.blockSignals(True)
                combo.setCurrentIndex(combo.findData(self.note_id))
                combo.blockSignals(False)
                raise
            self.note_id = combo.currentData()
            self.preferred_sub = self.note_id
            self.editor.blockSignals(True)
            note = self.service.data["notes"].get(self.note_id, {})
            self.editor.setHtml(note.get("text", ""))
            self.editor.blockSignals(False)
            self.note_status.setText(
                "Última alteração: " + note.get("updated_at", "nenhuma")
            )
            self.clear(ch)
            sub = next(s for s in subs if s["id"] == self.note_id)
            if sub["description"]:
                ch.addWidget(QLabel(sub["description"]))
            logs = [
                l
                for l in self.service.data["study_logs"]
                if l.get("subsession_id") == self.note_id
            ]
            ch.addWidget(
                QLabel(
                    "Tempo estudado: "
                    + self.hours(sum(l["seconds"] for l in logs))
                    + " · Último estudo: "
                    + max((l["date"] for l in logs), default="—")
                )
            )
            self.history_view(
                ch, self.service.history(self.subject_id, self.note_id), sub["target"]
            )

        combo.currentIndexChanged.connect(lambda: self.guard(load))
        self.editor.textChanged.connect(self.note_changed)
        load()

    def note_changed(self):
        self.note_dirty = True
        self.note_status.setText("Salvando…")
        self.note_save.start()

    def save_note(self):
        if (
            not self.note_id
            or not hasattr(self, "editor")
            or not self.note_save.isActive()
            and not getattr(self, "note_dirty", False)
        ):
            return
        self.note_save.stop()
        identifier = self.note_id
        try:
            self.service.note(identifier, self.editor.toHtml())
            self.note_status.setText("Salvo · " + datetime.now().strftime("%H:%M:%S"))
        except Exception:
            self.note_dirty = True
            self.note_status.setText("Não salvo — tente novamente antes de sair.")
            raise
        self.note_dirty = False
