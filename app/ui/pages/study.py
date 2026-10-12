from __future__ import annotations
from datetime import datetime, date, timedelta
from PySide6.QtWidgets import QHBoxLayout, QLabel, QComboBox, QCheckBox
from app.services.study import metrics, StudyTimer
from app.ui.widgets import Form, Chart


def fmt(value):
    return "—" if value is None else f"{value:.1f}%"


class StudyPages:
    def restore_active_timer(self):
        self.timer = None
        self.timer_link = None
        self.checkpoint_ticks = 0
        active = self.service.data["settings"].get("active_study")
        if active:
            self.timer = StudyTimer()
            self.timer.elapsed = active["seconds"]
            self.timer.start = active["start"]
            self.timer_link = dict(active["link"])
            self.subject_id = self.timer_link["subject_id"]

    def checkpoint_timer(self):
        if self.timer:
            active = self.service.save_active_study(
                self.timer_link, self.timer.seconds(), self.timer.start
            )
            self.timer_link = active["link"]
            self.checkpoint_ticks = 0

    def timer_pause(self):
        if self.timer:
            self.timer.pause()
            self.checkpoint_timer()

    def study_link_form(self, title):
        if not self.subject_choices():
            raise ValueError("Crie uma matéria primeiro.")
        subjects = sorted(self.subject_choices(), key=lambda s: s[1] != self.subject_id)
        form = Form(self, title, [("subject_id", "Matéria", "choice", subjects)])
        sessions = QComboBox()
        subs = QComboBox()
        form.layout.insertRow(1, "Sessão", sessions)
        form.layout.insertRow(2, "Subsessão", subs)

        def load_subs():
            subs.clear()
            subs.addItem("Nenhuma", None)
            for s in self.service.data["subsessions"]:
                if s["subject_id"] == form.widgets["subject_id"].currentData() and (
                    not sessions.currentData()
                    or s["session_id"] == sessions.currentData()
                ):
                    subs.addItem(s["title"], s["id"])

        def load():
            sessions.clear()
            sessions.addItem("Nenhuma", None)
            for s in self.service.data["sessions"]:
                if s["subject_id"] == form.widgets["subject_id"].currentData():
                    sessions.addItem(s["title"], s["id"])
            load_subs()

        form.widgets["subject_id"].currentIndexChanged.connect(load)
        sessions.currentIndexChanged.connect(load_subs)
        load()
        return form, sessions, subs

    def timer_start(self):
        if self.timer:
            self.timer.resume()
            self.checkpoint_timer()
            return
        form, sessions, subs = self.study_link_form("Iniciar sessão de estudo")
        if form.exec() == Form.Accepted:
            self.timer_link = {
                **form.values(),
                "session_id": sessions.currentData(),
                "subsession_id": subs.currentData(),
            }
            self.timer = StudyTimer()
            self.timer.resume()
            self.checkpoint_timer()
            self.statusBar().showMessage("Sessão de estudo iniciada.")
            self.refresh()

    def timer_end(self):
        if not self.timer:
            return
        seconds = self.timer.seconds()
        if seconds <= 0:
            return
        active = self.service.data["settings"].get("active_study")
        link = active["link"] if active else self.timer_link
        self.service.log(
            **link,
            seconds=seconds,
            start=self.timer.start,
            end=datetime.now().isoformat(),
            finish_active=True,
        )
        self.timer.finish()
        self.timer = None
        self.timer_link = None
        self.statusBar().showMessage("Sessão salva com sucesso.", 5000)
        self.refresh()

    def manual_time(self):
        form, sessions, subs = self.study_link_form("Registrar tempo manualmente")
        from PySide6.QtWidgets import QDoubleSpinBox, QDateTimeEdit
        from PySide6.QtCore import QDateTime

        duration = QDoubleSpinBox()
        duration.setRange(0.01, 100000)
        duration.setValue(60)
        start = QDateTimeEdit(QDateTime.currentDateTime().addSecs(-3600))
        start.setCalendarPopup(True)
        start.setDisplayFormat("dd/MM/yyyy HH:mm")
        form.layout.insertRow(3, "Minutos efetivamente estudados", duration)
        form.layout.insertRow(4, "Início", start)
        if form.exec() == Form.Accepted:
            when = start.dateTime().toPython()
            seconds = duration.value() * 60
            self.service.log(
                **form.values(),
                session_id=sessions.currentData(),
                subsession_id=subs.currentData(),
                seconds=seconds,
                start=when.isoformat(),
                end=(when + timedelta(seconds=seconds)).isoformat(),
            )
            self.refresh()

    def time_controls(self, box):
        self.title(box, "Tempo de estudo")
        actions = QHBoxLayout()
        box.addLayout(actions)
        self.button(actions, "Continuar" if self.timer else "Iniciar", self.timer_start)
        self.button(actions, "Pausar", self.timer_pause)
        self.button(actions, "Encerrar e salvar", self.timer_end)
        self.button(actions, "+ Tempo manual", self.manual_time)
        self.timer_label = QLabel()
        box.addWidget(self.timer_label)

    def statistics(self, box):
        self.title(
            box,
            "Estatísticas",
            "Os gráficos refletem exclusivamente seus registros locais.",
        )
        self.time_controls(box)
        data = self.service.data
        today = date.today()
        week = today - timedelta(days=today.weekday())
        weekly = (
            sum(
                l["seconds"]
                for l in data["study_logs"]
                if l["date"] >= week.isoformat()
            )
            / 3600
        )
        monthly = (
            sum(
                l["seconds"]
                for l in data["study_logs"]
                if l["date"][:7] == today.isoformat()[:7]
            )
            / 3600
        )
        box.addWidget(
            QLabel(
                f"Esta semana: {self.hours(weekly * 3600)}    Este mês: {self.hours(monthly * 3600)}"
            )
        )
        logs = sorted(data["study_logs"], key=lambda l: l["start"], reverse=True)
        names = {s["id"]: s["name"] for s in data["subjects"]}
        self.table(
            box,
            ["Data", "Matéria", "Tempo (min)", "Início", "Fim"],
            [
                [
                    l["date"],
                    names[l["subject_id"]],
                    f"{l['seconds'] / 60:.1f}",
                    l["start"][11:19],
                    l["end"][11:19],
                ]
                for l in logs
            ],
        )
        self.title(box, "Evolução global")
        box.addWidget(
            Chart(data["assessments"], data["settings"]["default_target"], self.dark)
        )
        import pyqtgraph as pg

        plot = pg.PlotWidget()
        plot.setBackground("#202938" if self.dark else "#F3F7FC")
        plot.setLabel("left", "Desempenho (%)")
        subjects = data["subjects"]
        scores = [metrics(self.service.history(s["id"]))["mean"] for s in subjects]
        indices = [i for i, score in enumerate(scores) if score is not None]
        plot.addItem(
            pg.BarGraphItem(
                x=indices,
                height=[scores[i] for i in indices],
                width=0.65,
                brush="#659ED5",
            )
        )
        plot.getAxis("bottom").setTicks(
            [[(i, s["name"]) for i, s in enumerate(subjects)]]
        )
        plot.setYRange(0, 100)
        plot.setMinimumHeight(250)
        box.addWidget(plot)
        self.title(box, "Horas por semana")
        hours = {}
        for l in logs:
            day = date.fromisoformat(l["date"])
            monday = (day - timedelta(days=day.weekday())).isoformat()
            hours[monday] = hours.get(monday, 0) + l["seconds"] / 3600
        weeks = sorted(hours)
        hp = pg.PlotWidget()
        hp.setBackground("#202938" if self.dark else "#F3F7FC")
        hp.setLabel("left", "Horas")
        hp.addItem(
            pg.BarGraphItem(
                x=list(range(len(weeks))),
                height=[hours[w] for w in weeks],
                width=0.65,
                brush="#319B70",
            )
        )
        hp.getAxis("bottom").setTicks([list(enumerate(weeks))])
        hp.setMinimumHeight(240)
        box.addWidget(hp)
        ranking = sorted(
            subjects,
            key=lambda s: metrics(self.service.history(s["id"]))["trend"],
            reverse=True,
        )
        self.table(
            box,
            ["Matéria", "Evolução (pp)", "Situação"],
            [
                [
                    s["name"],
                    f"{metrics(self.service.history(s['id']))['trend']:+.1f}",
                    "Sem avaliações"
                    if metrics(self.service.history(s["id"]))["last"] is None
                    else "Reforçar"
                    if metrics(self.service.history(s["id"]))["last"] < s["target"]
                    else "Na meta",
                ]
                for s in ranking
            ],
        )

    def bootcamp_view(self, box):
        self.title(
            box,
            "Bootcamps",
            "Planeje semanas intensivas e semanas de reforço sem limitar outras matérias.",
        )
        self.button(box, "+ Novo bootcamp", lambda: self.edit_bootcamp(None))
        items = [
            b
            for b in self.service.data["bootcamps"]
            if b["subject_id"] == self.subject_id
        ]
        from PySide6.QtWidgets import QProgressBar

        for b in items:
            progress, approved = self.service.bootcamp_status(b)
            box.addWidget(
                QLabel(
                    f"{b['name']} · {b['start']} → {b['end']} · {'Aprovado' if approved else 'Em andamento'} · meta {b['target']}%\n{b['plan']}"
                )
            )
            bar = QProgressBar()
            bar.setValue(round(progress))
            bar.setFormat(f"%p% de {b['hours']:g} h")
            box.addWidget(bar)
            actions = QHBoxLayout()
            box.addLayout(actions)
            self.button(
                actions, "Editar / avaliação final", lambda b=b: self.edit_bootcamp(b)
            )
            self.button(
                actions, "Excluir bootcamp", lambda b=b: self.remove_bootcamp(b)
            )

    def remove_bootcamp(self, b):
        if self.confirm(
            "Excluir este planejamento de bootcamp? Os estudos e avaliações serão preservados."
        ):
            self.service.delete("bootcamps", b["id"])
            self.refresh()

    def edit_bootcamp(self, existing):
        b = existing or {}
        sessions = [
            s
            for s in self.service.data["sessions"]
            if s["subject_id"] == self.subject_id
        ]
        assessments = [("Ainda não realizada", None)] + [
            (a["name"] + " · " + fmt(a["percentage"]), a["id"])
            for a in self.service.history(self.subject_id)
        ]
        assessments.sort(key=lambda p: p[1] != b.get("final_assessment"))
        fields = [
            ("name", "Nome", "text", b.get("name", "")),
            ("start", "Data inicial", "date", b.get("start", date.today().isoformat())),
            (
                "end",
                "Data final",
                "date",
                b.get("end", (date.today() + timedelta(days=6)).isoformat()),
            ),
            (
                "day_text",
                "Dias: 1=seg … 7=dom",
                "text",
                ",".join(str(d + 1) for d in b.get("days", [0, 1, 2, 3, 4])),
            ),
            ("hours", "Meta de horas", "number", b.get("hours", 24)),
            (
                "target",
                "Meta de aprovação (%)",
                "percent",
                b.get("target", self.subject()["target"]),
            ),
            ("plan", "Plano por dia / revisão", "long", b.get("plan", "")),
            ("final_assessment", "Avaliação final", "choice", assessments),
        ]
        form = Form(self, "Planejar bootcamp", fields)
        checks = {}
        for s in sessions:
            w = QCheckBox(s["title"])
            w.setChecked(s["id"] in b.get("sessions", []))
            checks[s["id"]] = w
            form.layout.insertRow(form.layout.rowCount() - 1, w)
        if form.exec() == Form.Accepted:
            v = form.values()
            if not v["name"].strip() or v["hours"] <= 0 or v["end"] < v["start"]:
                raise ValueError(
                    "Informe nome, período válido e meta de horas positiva."
                )
            try:
                days = [
                    int(x.strip()) - 1
                    for x in v.pop("day_text").split(",")
                    if x.strip()
                ]
            except ValueError:
                raise ValueError("Informe dias de 1 a 7.")
            if not days or any(x < 0 or x > 6 for x in days):
                raise ValueError("Informe dias de 1 a 7.")
            v["days"] = sorted(set(days))
            v["sessions"] = [k for k, w in checks.items() if w.isChecked()]
            v["subject_id"] = self.subject_id
            if existing:
                self.service.update("bootcamps", b["id"], **v)
            else:
                self.service.add("bootcamps", **v)
            self.refresh()
