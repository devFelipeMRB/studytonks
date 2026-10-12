from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QComboBox,
    QMessageBox,
    QFileDialog,
    QSystemTrayIcon,
    QCheckBox,
    QSpinBox,
)
from app.services.reminders import set_autostart, autostart_status


def fmt(value):
    return "—" if value is None else f"{value:.1f}%"


class SettingsPages:
    def settings_page(self, box):
        self.title(
            box,
            "Configurações",
            "Preferências salvas imediatamente. Seus dados ficam fora do executável.",
        )
        settings = self.service.data["settings"]
        actual_autostart = autostart_status(
            sys.executable,
            None
            if getattr(sys, "frozen", False)
            else str(Path(__file__).parents[3] / "main.py"),
        )
        theme = QComboBox()
        for label, value in [
            ("Automático", "automatic"),
            ("Claro", "light"),
            ("Escuro", "dark"),
        ]:
            theme.addItem(label, value)
        theme.setCurrentIndex(theme.findData(settings["theme"]))
        box.addWidget(QLabel("Tema"))
        box.addWidget(theme)

        def change_theme():
            self.service.settings(theme=theme.currentData())
            self.apply_theme()
            self.refresh()

        theme.currentIndexChanged.connect(lambda: self.guard(change_theme))
        target = QSpinBox()
        target.setRange(0, 100)
        target.setValue(settings["default_target"])
        box.addWidget(QLabel("Meta padrão (%)"))
        box.addWidget(target)
        target.valueChanged.connect(
            lambda v: self.guard(lambda: self.service.settings(default_target=v))
        )
        hours = QComboBox()
        hours.addItem("Horas decimais", "decimal")
        hours.addItem("Horas e minutos", "clock")
        hours.setCurrentIndex(hours.findData(settings["hours_format"]))
        box.addWidget(QLabel("Formato de horas"))
        box.addWidget(hours)
        hours.currentIndexChanged.connect(
            lambda: self.guard(
                lambda: self.service.settings(hours_format=hours.currentData())
            )
        )
        periods = QComboBox()
        for text, days in [
            ("Histórico completo", 0),
            ("7 dias", 7),
            ("30 dias", 30),
            ("90 dias", 90),
        ]:
            periods.addItem(text, days)
        periods.setCurrentIndex(periods.findData(settings["chart_days"]))
        box.addWidget(QLabel("Período padrão dos gráficos"))
        box.addWidget(periods)
        periods.currentIndexChanged.connect(
            lambda: self.guard(
                lambda: self.service.settings(chart_days=periods.currentData())
            )
        )
        for key, label in [
            ("notifications", "Ativar notificações"),
            ("autostart", "Iniciar Studytonks junto com o Windows"),
            ("minimized", "Iniciar minimizado na bandeja"),
            ("background", "Continuar funcionando em segundo plano"),
        ]:
            w = QCheckBox(label)
            w.setChecked(actual_autostart if key == "autostart" else settings[key])
            box.addWidget(w)
            if key == "autostart" and sys.platform != "win32":
                w.setEnabled(False)
                w.setToolTip("Disponível no Windows 10/11.")
            if (
                key in ("minimized", "background")
                and not QSystemTrayIcon.isSystemTrayAvailable()
            ):
                w.setEnabled(False)
                w.setToolTip("Bandeja indisponível neste ambiente.")

            def changed(enabled, key=key, w=w):
                try:
                    if key == "autostart":
                        if enabled and not self.confirm(
                            "Autorizar Studytonks a iniciar junto com o Windows?"
                        ):
                            w.blockSignals(True)
                            w.setChecked(False)
                            w.blockSignals(False)
                            return
                        set_autostart(
                            enabled,
                            sys.executable,
                            None
                            if getattr(sys, "frozen", False)
                            else str(Path(__file__).parents[3] / "main.py"),
                        )
                    self.service.settings(**{key: enabled})
                except Exception:
                    w.blockSignals(True)
                    w.setChecked(not enabled)
                    w.blockSignals(False)
                    raise

            w.toggled.connect(
                lambda enabled, changed=changed: self.guard(lambda: changed(enabled))
            )
        box.addWidget(
            QLabel(
                "Notificações respeitam as configurações do Windows. Lembretes exigem o aplicativo em execução."
            )
        )
        backup_days = QSpinBox()
        backup_days.setRange(0, 365)
        backup_days.setValue(settings["backup_days"])
        box.addWidget(QLabel("Backup automático a cada N dias (0 desativa)"))
        box.addWidget(backup_days)
        backup_days.valueChanged.connect(
            lambda v: self.guard(lambda: self.service.settings(backup_days=v))
        )
        box.addWidget(QLabel("Pasta de dados: " + str(self.service.store.root)))
        box.addWidget(
            QLabel(
                "Pasta de backups: "
                + (settings["backup_dir"] or str(self.service.store.root / "backups"))
            )
        )
        self.button(box, "Escolher pasta de backups", self.choose_backup_directory)
        self.button(
            box,
            "Abrir pasta de dados",
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.service.store.root))
            ),
        )
        actions = QHBoxLayout()
        box.addLayout(actions)
        self.button(actions, "Criar backup manual", self.manual_backup)
        self.button(actions, "Exportar backup ZIP", self.export_backup)
        self.button(actions, "Importar / restaurar backup", self.import_backup)
        box.addStretch()

    def choose_backup_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Diretório de backups")
        if folder:
            self.service.settings(backup_dir=folder)
            self.refresh()

    def manual_backup(self):
        settings = self.service.data["settings"]
        folder = Path(settings["backup_dir"] or self.service.store.root / "backups")
        folder.mkdir(parents=True, exist_ok=True)
        result = self.service.store.backup(
            folder / f"manual-{datetime.now():%Y%m%d-%H%M%S%f}.zip"
        )
        QMessageBox.information(self, "Backup criado", str(result))

    def export_backup(self):
        file, _ = QFileDialog.getSaveFileName(
            self, "Exportar backup", "Studytonks-backup.zip", "ZIP (*.zip)"
        )
        if file:
            self.service.store.backup(file)
            QMessageBox.information(
                self, "Backup exportado", "Backup criado com sucesso."
            )

    def import_backup(self):
        if self.timer:
            raise ValueError("Encerre a sessão de estudo antes de restaurar um backup.")
        file, _ = QFileDialog.getOpenFileName(
            self, "Restaurar backup", "", "ZIP (*.zip)"
        )
        if not file:
            return
        self.service.store.inspect_backup(file)
        if self.confirm(
            "Substituir os dados atuais pelos dados do backup? Uma cópia de segurança será criada antes."
        ):
            self.save_note()
            self.service.store.restore(file)
            self.subject_id = None
            self.restore_active_timer()
            self.apply_theme()
            self.refresh()
