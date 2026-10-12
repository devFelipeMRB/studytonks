from datetime import datetime
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QDoubleSpinBox,
    QComboBox,
    QDialogButtonBox,
    QDateEdit,
    QDateTimeEdit,
    QCheckBox,
    QLabel,
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QMessageBox,
)
from PySide6.QtCore import QDate, QDateTime
import pyqtgraph as pg
from app.services.study import assessment_order


class Form(QDialog):
    def __init__(self, parent, title, fields):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        self.layout = QFormLayout(body)
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.resize(540, 640)
        self.widgets = {}
        self.on_submit = None
        self.result_value = None
        for key, label, kind, value in fields:
            if kind == "text":
                widget = QLineEdit(str(value or ""))
            elif kind == "long":
                widget = QTextEdit()
                widget.setPlainText(value or "")
                widget.setMaximumHeight(100)
            elif kind == "number":
                widget = QDoubleSpinBox()
                widget.setRange(0, 1000000)
                widget.setDecimals(2)
                widget.setValue(value)
            elif kind == "percent":
                widget = QDoubleSpinBox()
                widget.setRange(0, 100)
                widget.setValue(value)
            elif kind == "date":
                widget = QDateEdit(QDate.fromString(value, "yyyy-MM-dd"))
                widget.setCalendarPopup(True)
                widget.setDisplayFormat("dd/MM/yyyy")
            elif kind == "datetime":
                widget = QDateTimeEdit(QDateTime.fromString(value, "yyyy-MM-ddTHH:mm"))
                widget.setCalendarPopup(True)
                widget.setDisplayFormat("dd/MM/yyyy HH:mm")
            elif kind == "check":
                widget = QCheckBox()
                widget.setChecked(value)
            elif kind == "choice":
                widget = QComboBox()
                for text, data in value:
                    widget.addItem(text, data)
            self.widgets[key] = widget
            self.layout.addRow(label, widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def accept(self):
        if self.on_submit is not None:
            try:
                self.result_value = self.on_submit(self.values())
            except Exception as exc:
                QMessageBox.warning(self, "Revise os dados", str(exc))
                return
        super().accept()

    def values(self):
        result = {}
        for key, w in self.widgets.items():
            if isinstance(w, QLineEdit):
                value = w.text()
            elif isinstance(w, QTextEdit):
                value = w.toPlainText()
            elif isinstance(w, QDoubleSpinBox):
                value = w.value()
            elif isinstance(w, QComboBox):
                value = w.currentData()
            elif isinstance(w, QDateTimeEdit) and not isinstance(w, QDateEdit):
                value = w.dateTime().toString("yyyy-MM-ddTHH:mm")
            elif isinstance(w, QDateEdit):
                value = w.date().toString("yyyy-MM-dd")
            else:
                value = w.isChecked()
            result[key] = value
        return result


class Chart(QWidget):
    def __init__(self, history, target=85, dark=False):
        super().__init__()
        layout = QVBoxLayout(self)
        if not history:
            layout.addWidget(QLabel("Seu progresso começa com a primeira avaliação."))
        plot = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem()})
        plot.setBackground("#202938" if dark else "#F3F7FC")
        plot.setLabel("left", "Desempenho", units="%")
        plot.setYRange(0, 100, padding=0.05)
        plot.showGrid(x=True, y=True, alpha=0.12)
        plot.addItem(
            pg.InfiniteLine(
                target,
                angle=0,
                pen=pg.mkPen(
                    "#659ED5",
                    style=__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.DashLine,
                ),
            )
        )
        history = sorted(history, key=assessment_order)
        xs = [datetime.fromisoformat(a["date"]).timestamp() for a in history]
        ys = [a["percentage"] for a in history]
        for i in range(1, len(xs)):
            color = (
                "#319B70"
                if ys[i] > ys[i - 1]
                else "#D65B65"
                if ys[i] < ys[i - 1]
                else "#659ED5"
            )
            plot.plot(
                xs[i - 1 : i + 1], ys[i - 1 : i + 1], pen=pg.mkPen(color, width=2)
            )
        spots = [
            {"pos": (x, y), "data": a, "brush": "#659ED5"}
            for x, y, a in zip(xs, ys, history)
        ]
        scatter = pg.ScatterPlotItem(
            spots=spots,
            size=10,
            hoverable=True,
            tip=lambda x, y, data: f"{data['date']} · {data['name']} · {y:.1f}%",
        )
        plot.addItem(scatter)
        self.plot = plot
        layout.addWidget(plot)
        self.setMinimumHeight(240)
