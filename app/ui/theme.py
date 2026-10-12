"""Shared Qt palette and restrained desktop styling."""


def stylesheet(dark: bool) -> str:
    bg, surface, text, muted, border, blue, selection = (
        ("#151B25", "#202938", "#E6EDF7", "#A7B6CC", "#334158", "#8ABDEB", "#263C55")
        if dark
        else (
            "#FAF9F6",
            "#F3F7FC",
            "#263B51",
            "#667C93",
            "#E5EAF0",
            "#659ED5",
            "#D7EAFE",
        )
    )
    return f"""
    QWidget {{ background: {bg}; color: {text}; font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 14px; }}
    QLabel {{ background: transparent; }}
    QWidget#sidebar {{ background: {surface}; border-right: 1px solid {border}; }}
    QWidget#sidebar QLabel {{ background: transparent; }}
    QLabel#brand {{ font-size: 23px; font-weight: 700; }}
    QLabel#tagline, QLabel#muted {{ color: {muted}; font-size: 12px; }}
    QLabel#heading {{ font-size: 27px; font-weight: 600; padding-bottom: 4px; }}
    QLabel#sectionHeading {{ font-size: 19px; font-weight: 600; padding-top: 12px; padding-bottom: 8px; }}
    QPushButton {{ background: {surface}; border: 1px solid {border}; border-radius: 8px; padding: 10px 16px; }}
    QPushButton:hover {{ background: {selection}; border-color: {blue}; }}
    QPushButton:pressed {{ background: {blue}; color: #151B25; }}
    QPushButton:disabled {{ color: {muted}; border-color: {border}; }}
    QPushButton#primary {{ background: {selection}; border: 1px solid {blue}; font-weight: 600; }}
    QPushButton#primary:hover {{ background: {blue}; color: #151B25; }}
    QPushButton:focus, QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border: 1px solid {blue}; }}
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {{ border: 1px solid {border}; border-radius: 7px; padding: 9px; background: {surface}; selection-background-color: {selection}; selection-color: {text}; }}
    QComboBox {{ min-height: 22px; }}
    QListWidget#navigation {{ border: 0; background: transparent; padding-top: 12px; outline: none; }}
    QListWidget#navigation::item {{ padding: 12px 10px; margin-bottom: 4px; border-radius: 8px; }}
    QListWidget#navigation::item:hover {{ background: {selection}; }}
    QListWidget#navigation::item:selected {{ background: {selection}; color: {text}; font-weight: 600; }}
    QTableWidget, QTreeWidget {{ border: 1px solid {border}; border-radius: 10px; alternate-background-color: {surface}; gridline-color: {border}; outline: none; }}
    QTreeWidget::item {{ padding: 9px; }}
    QTableWidget::item:selected, QTreeWidget::item:selected {{ background: {selection}; color: {text}; }}
    QHeaderView::section {{ background: {surface}; padding: 12px; border: 0; font-size: 12px; font-weight: 600; }}
    QLabel#card {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; padding: 16px; font-size: 16px; }}
    QFrame#metricCard, QFrame#emptyState {{ background: {surface}; border: 1px solid {border}; border-radius: 12px; }}
    QFrame#metricCard QLabel, QFrame#emptyState QLabel {{ background: transparent; border: 0; }}
    QLabel#metricValue {{ font-size: 25px; font-weight: 650; }}
    QLabel#metricLabel {{ font-size: 12px; color: {muted}; }}
    QLabel#emptyTitle {{ font-size: 22px; font-weight: 600; }}
    QLabel#emptyDescription {{ color: {muted}; font-size: 14px; }}
    QScrollArea {{ border: 0; }}
    QScrollBar:vertical {{ background: {bg}; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {border}; min-height: 28px; border-radius: 5px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QProgressBar {{ border: 1px solid {border}; border-radius: 7px; min-height: 22px; text-align: center; }}
    QProgressBar::chunk {{ background: {"#57C798" if dark else "#319B70"}; border-radius: 6px; }}
    QStatusBar {{ color: {muted}; font-size: 12px; border-top: 1px solid {border}; }}
    """
