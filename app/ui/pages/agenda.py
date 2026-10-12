from __future__ import annotations
from datetime import datetime, timedelta
from PySide6.QtWidgets import QHBoxLayout, QSystemTrayIcon
from app.services.reminders import occurrence


def fmt(value):
    return "—" if value is None else f"{value:.1f}%"


class AgendaPages:
    def upcoming(self):
        now = datetime.now()
        result = []
        for r in self.service.data["reminders"]:
            if not r.get("enabled", True):
                continue
            base = datetime.fromisoformat(r["when"])
            if r["recurrence"] == "once":
                if base >= now:
                    result.append((base, r))
                continue
            for delta in range(8):
                day = now.date() + timedelta(days=delta)
                candidate = datetime.combine(day, base.time())
                if candidate >= max(now, base) and (
                    r["recurrence"] == "daily" or candidate.weekday() in r["days"]
                ):
                    result.append((candidate, r))
                    break
        return sorted(result, key=lambda x: x[0])

    def tick(self):
        if self.timer:
            if self.timer.since is not None:
                self.checkpoint_ticks += 1
                if self.checkpoint_ticks >= 30:
                    self.guard(self.checkpoint_timer)
            seconds = int(self.timer.seconds())
            text = f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}" + (
                " · pausado" if self.timer.since is None else " · estudando"
            )
            self.statusBar().showMessage(text)
            if self.nav.currentRow() == 7 and hasattr(self, "timer_label"):
                self.timer_label.setText(text)
        upcoming = self.upcoming()
        self.next_action.setText(
            "Próximo lembrete: " + (upcoming[0][1]["title"] if upcoming else "nenhum")
        )
        if not self.service.data["settings"]["notifications"]:
            return
        for r in list(self.service.data["reminders"]):
            token = occurrence(r, datetime.now())
            if (
                token
                and QSystemTrayIcon.isSystemTrayAvailable()
                and QSystemTrayIcon.supportsMessages()
            ):
                try:
                    self.service.update("reminders", r["id"], last_fired=token)
                    self.tray.showMessage(
                        "Studytonks", r["title"], QSystemTrayIcon.Information, 10000
                    )
                except Exception as exc:
                    self.statusBar().showMessage(
                        "Falha ao processar lembrete: " + str(exc)
                    )

    def agenda(self, box):
        self.title(
            box,
            "Agenda e lembretes",
            "Lembretes locais exigem o aplicativo aberto, inclusive minimizado na bandeja.",
        )
        self.button(box, "+ Novo lembrete", lambda: self.edit_reminder(None))
        items = self.service.data["reminders"]
        names = dict((identifier, name) for name, identifier in self.subject_choices())
        table = self.table(
            box,
            ["Lembrete", "Início", "Repetição", "Matéria", "Ativo"],
            [
                [
                    r["title"],
                    r["when"],
                    r["recurrence"],
                    names.get(r.get("subject_id"), "—"),
                    "Sim" if r["enabled"] else "Não",
                ]
                for r in items
            ],
        )
        actions = QHBoxLayout()
        box.addLayout(actions)
        self.button(
            actions, "Editar", lambda: self.edit_reminder(self.selected(table, items))
        )

        def remove():
            r = self.selected(table, items)
            if self.confirm("Excluir este lembrete?"):
                self.service.delete("reminders", r["id"])
                self.refresh()

        self.button(actions, "Excluir", remove)
        box.addStretch()

    def edit_reminder(self, existing):
        r = existing or {}
        choices = [
            ("Único", "once"),
            ("Diário", "daily"),
            ("Semanal / dias específicos", "weekly"),
        ]
        choices.sort(key=lambda p: p[1] != r.get("recurrence", "once"))
        subjects = [("Nenhuma", None)] + self.subject_choices()
        subjects.sort(key=lambda p: p[1] != r.get("subject_id"))
        sessions = [("Nenhuma", None)] + [
            (s["title"], s["id"]) for s in self.service.data["sessions"]
        ]
        sessions.sort(key=lambda p: p[1] != r.get("session_id"))

        def save(v):
            if not v["title"].strip():
                raise ValueError("Informe o lembrete.")
            try:
                days = [
                    int(x.strip()) - 1
                    for x in v.pop("day_text").split(",")
                    if x.strip()
                ]
            except ValueError:
                raise ValueError("Dias: use números de 1 (segunda) a 7 (domingo).")
            if (
                any(d < 0 or d > 6 for d in days)
                or v["recurrence"] == "weekly"
                and not days
            ):
                raise ValueError("Informe dias válidos de 1 a 7.")
            v["days"] = sorted(set(days))
            v["last_fired"] = None
            if v["session_id"]:
                session = next(
                    s
                    for s in self.service.data["sessions"]
                    if s["id"] == v["session_id"]
                )
                if v["subject_id"] and session["subject_id"] != v["subject_id"]:
                    raise ValueError("Sessão pertence a outra matéria.")
                v["subject_id"] = session["subject_id"]
            if existing:
                self.service.update("reminders", existing["id"], **v)
            else:
                self.service.add("reminders", **v)

        self.dialog(
            "Editar lembrete" if r else "Novo lembrete",
            [
                ("title", "Mensagem", "text", r.get("title", "")),
                (
                    "when",
                    "Primeiro horário",
                    "datetime",
                    r.get("when", datetime.now().strftime("%Y-%m-%dT%H:%M")),
                ),
                ("recurrence", "Repetição", "choice", choices),
                (
                    "day_text",
                    "Dias: 1=seg … 7=dom",
                    "text",
                    ",".join(str(d + 1) for d in r.get("days", [0, 1, 2, 3, 4])),
                ),
                ("subject_id", "Matéria", "choice", subjects),
                ("session_id", "Sessão", "choice", sessions),
                ("enabled", "Ativo", "check", r.get("enabled", True)),
            ],
            save,
        )
