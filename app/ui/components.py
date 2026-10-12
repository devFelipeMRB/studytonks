from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QGridLayout,
)


class MetricCard(QFrame):
    def __init__(self, value: str, label: str):
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        amount = QLabel(value)
        amount.setObjectName("metricValue")
        caption = QLabel(label)
        caption.setObjectName("metricLabel")
        caption.setWordWrap(True)
        layout.addWidget(amount)
        layout.addWidget(caption)
        self.setMinimumHeight(96)


class EmptyState(QFrame):
    def __init__(
        self, title: str, description: str, action_label: str = "", action=None
    ):
        super().__init__()
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 30, 28, 30)
        layout.setSpacing(12)
        icon = QLabel()
        icon.setAlignment(Qt.AlignCenter)
        icon.setPixmap(
            QPixmap(
                str(Path(__file__).parents[1] / "assets" / "studytonks.png")
            ).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        heading = QLabel(title)
        heading.setObjectName("emptyTitle")
        heading.setAlignment(Qt.AlignCenter)
        heading.setWordWrap(True)
        body = QLabel(description)
        body.setObjectName("emptyDescription")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        layout.addWidget(icon)
        layout.addWidget(heading)
        layout.addWidget(body)
        if action_label and action:
            button = QPushButton(action_label)
            button.setObjectName("primary")
            button.setMaximumWidth(280)
            button.clicked.connect(action)
            layout.addWidget(button, 0, Qt.AlignCenter)


class MetricGrid(QWidget):
    def __init__(self, values):
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.cards = [MetricCard(value, label) for value, label in values]
        self.columns = 0
        self.reflow()

    def reflow(self):
        columns = 5 if self.width() >= 850 else 3 if self.width() >= 600 else 2
        if columns == self.columns:
            return
        self.columns = columns
        for card in self.cards:
            self.grid.removeWidget(card)
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()
