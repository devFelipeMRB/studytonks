from __future__ import annotations
from datetime import datetime, date, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidgetItem,
    QLineEdit,
    QComboBox,
    QTreeWidget,
    QTreeWidgetItem,
)
from app.services.study import metrics
from app.ui.widgets import Chart
from app.ui.components import MetricGrid, EmptyState


def fmt(value):
    return "—" if value is None else f"{value:.1f}%"


class SubjectPages:
    def dashboard(self, box):
        now = datetime.now()
        greeting = (
            "Bom dia"
            if now.hour < 12
            else "Boa tarde"
            if now.hour < 18
            else "Boa noite"
        )
        self.title(
            box,
            f"{greeting}. Vamos aprender?",
            now.strftime("%d/%m/%Y") + " · Studytonks",
        )
        actions = QHBoxLayout()
        box.addLayout(actions)
        self.button(actions, "+ Nova matéria", self.new_subject).setObjectName(
            "primary"
        )
        self.button(actions, "Alternar tema", self.toggle_theme)
        actions.addStretch()
        data = self.service.data
        subjects = [s for s in data["subjects"] if not s["archived"]]
        grades = metrics(data["assessments"])
        approved = sum(
            m["last"] is not None and m["last"] >= s["target"]
            for s in subjects
            for m in [metrics(self.service.history(s["id"]))]
        )
        reminders = self.upcoming()
        box.addWidget(
            MetricGrid(
                [
                    (str(len(subjects)), "Matérias ativas"),
                    (
                        self.hours(sum(l["seconds"] for l in data["study_logs"])),
                        "Tempo de estudo",
                    ),
                    (str(grades["count"]), "Avaliações realizadas"),
                    (fmt(grades["mean"]), "Média geral"),
                    (str(approved), "Matérias na meta"),
                ]
            )
        )
        box.addWidget(
            QLabel(
                "Próxima sessão: "
                + (
                    reminders[0][1]["title"]
                    + " · "
                    + reminders[0][0].strftime("%d/%m %H:%M")
                    if reminders
                    else "nenhum lembrete agendado"
                )
            )
        )
        self.subject_table(box, subjects)
        box.addStretch()

    def toggle_theme(self):
        self.service.settings(theme="light" if self.dark else "dark")
        self.apply_theme()
        self.refresh()

    def subjects_page(self, box):
        self.title(
            box, "Matérias", "Organize seus objetivos e acompanhe cada conquista."
        )
        self.button(box, "+ Nova matéria", self.new_subject)
        self.subject_table(box, self.service.data["subjects"])

    def subject_table(self, box, subjects):
        heading = QLabel("Suas matérias")
        heading.setObjectName("sectionHeading")
        box.addWidget(heading)
        if not subjects:
            archived = bool(self.service.data["subjects"])
            box.addWidget(
                EmptyState(
                    "Tudo começa com a primeira matéria"
                    if not archived
                    else "Suas matérias estão arquivadas",
                    "Escolha o que quer aprender. Depois, organize sessões, registre seus estudos e acompanhe cada conquista."
                    if not archived
                    else "Abra a área Matérias para desarquivar ou crie um novo objetivo.",
                    "Criar minha primeira matéria"
                    if not archived
                    else "Criar nova matéria",
                    lambda: self.guard(self.new_subject),
                )
            )
            return
        search = QLineEdit()
        search.setPlaceholderText("⌕ Pesquisar matérias, descrição ou palavras-chave…")
        sort = QComboBox()
        sort.addItems(["Nome", "Criação", "Última atividade", "Desempenho", "Evolução"])
        row = QHBoxLayout()
        row.addWidget(search)
        row.addWidget(sort)
        box.addLayout(row)
        table = self.table(
            box,
            ["Matéria", "Sessões", "Última nota", "Média", "Evolução", "Status"],
            [],
        )
        empty = EmptyState(
            "Nenhum resultado encontrado",
            "Tente outro nome, descrição ou palavra-chave.",
        )
        box.addWidget(empty)
        visible = []

        def fill():
            import unicodedata

            def norm(s):
                return "".join(
                    c
                    for c in unicodedata.normalize("NFKD", s.casefold())
                    if not unicodedata.combining(c)
                )

            terms = norm(search.text()).split()
            visible[:] = [
                s
                for s in subjects
                if all(t in norm(s["name"] + " " + s["description"]) for t in terms)
            ]

            def key(s):
                m = metrics(self.service.history(s["id"]))
                activity = max(
                    [s["created_at"], s.get("updated_at", "")]
                    + [a["date"] for a in self.service.history(s["id"])]
                    + [
                        l["end"]
                        for l in self.service.data["study_logs"]
                        if l["subject_id"] == s["id"]
                    ]
                )
                return [
                    s["name"].casefold(),
                    s["created_at"],
                    activity,
                    m["last"] or 0,
                    m["trend"],
                ][sort.currentIndex()]

            visible.sort(key=key, reverse=sort.currentIndex() > 0)
            table.setRowCount(len(visible))
            for i, s in enumerate(visible):
                m = metrics(self.service.history(s["id"]))
                status = (
                    "Arquivada"
                    if s["archived"]
                    else "Sem avaliações"
                    if m["last"] is None
                    else "Aprovado"
                    if m["last"] >= s["target"]
                    else "Reforçar"
                )
                values = [
                    s["icon"] + " " + s["name"],
                    sum(
                        x["subject_id"] == s["id"]
                        for x in self.service.data["sessions"]
                    ),
                    fmt(m["last"]),
                    fmt(m["mean"]),
                    f"{'↑' if m['trend'] > 0 else '↓' if m['trend'] < 0 else '→'} {m['trend']:+.1f} pp",
                    status,
                ]
                for j, v in enumerate(values):
                    table.setItem(i, j, QTableWidgetItem(str(v)))
                from PySide6.QtGui import QColor

                table.item(i, 0).setForeground(QColor(s["color"]))
            empty.setVisible(not visible)
            table.setVisible(bool(visible))
            open_button.setEnabled(bool(visible))
            table.resizeColumnsToContents()

        search.textChanged.connect(fill)
        sort.currentIndexChanged.connect(fill)
        table.cellDoubleClicked.connect(
            lambda r, c: self.open_subject(visible[r]["id"])
        )
        open_button = self.button(
            box,
            "Abrir matéria selecionada",
            lambda: self.open_subject(self.selected(table, visible)["id"]),
        )
        fill()

    def open_subject(self, identifier):
        self.subject_id = identifier
        self.nav.setCurrentRow(2)
        self.refresh()

    def new_subject(self):
        self.edit_subject(None)

    def edit_subject(self, subject):
        s = subject or {
            "name": "",
            "description": "",
            "color": "#659ED5",
            "icon": "📘",
            "target": self.service.data["settings"]["default_target"],
        }
        fields = [
            ("name", "Nome", "text", s["name"]),
            ("description", "Descrição e palavras-chave", "long", s["description"]),
            ("color", "Cor (#RRGGBB)", "text", s["color"]),
            ("icon", "Ícone (símbolo)", "text", s["icon"]),
            ("target", "Meta (%)", "percent", s["target"]),
        ]

        def save(v):
            from PySide6.QtGui import QColor

            if not v["name"].strip():
                raise ValueError("Informe o nome.")
            if not QColor(v["color"]).isValid():
                raise ValueError("Cor inválida.")
            if subject:
                self.service.update("subjects", subject["id"], **v)
            else:
                self.subject_id = self.service.subject(**v)["id"]

        self.dialog("Editar matéria" if subject else "Nova matéria", fields, save)

    def details(self, box):
        self.title(box, "Sua jornada")
        if not self.selector(box):
            return
        s = self.subject()
        self.title(box, s["icon"] + " " + s["name"], s["description"])
        total = sum(
            l["seconds"]
            for l in self.service.data["study_logs"]
            if l["subject_id"] == s["id"]
        )
        summary = metrics(self.service.history(s["id"]))
        status = (
            "Arquivada"
            if s["archived"]
            else "Sem avaliações"
            if summary["last"] is None
            else "Aprovado"
            if summary["last"] >= s["target"]
            else "Reforçar"
        )
        card = QLabel(
            f"{self.hours(total)} estudadas · {summary['count']} avaliações · meta {s['target']:.1f}% · {status}"
        )
        card.setObjectName("card")
        box.addWidget(card)
        actions = QHBoxLayout()
        box.addLayout(actions)
        self.button(actions, "Editar", lambda: self.edit_subject(s))
        self.button(
            actions,
            "Desarquivar" if s["archived"] else "Arquivar",
            lambda: (
                self.service.update("subjects", s["id"], archived=not s["archived"]),
                self.refresh(),
            ),
        )
        self.button(actions, "Excluir", lambda: self.delete_subject(s))
        self.button(actions, "+ Registrar avaliação", self.new_assessment)
        self.button(actions, "Sessões", lambda: self.nav.setCurrentRow(3))
        self.history_view(box, self.service.history(s["id"]), s["target"])
        self.bootcamp_view(box)

    def delete_subject(self, s):
        if self.confirm(
            f"Excluir permanentemente {s['name']} e todos os dados vinculados?"
        ):
            self.service.delete("subjects", s["id"])
            self.subject_id = None
            self.refresh()

    def history_view(self, box, history, target):
        period = QComboBox()
        period.addItems(
            ["Todo o histórico", "Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias"]
        )
        setting = self.service.data["settings"].get("chart_days", 0)
        period.setCurrentIndex({0: 0, 7: 1, 30: 2, 90: 3}.get(setting, 0))
        box.addWidget(period)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        box.addWidget(holder)

        def draw():
            self.clear(hl)
            days = [0, 7, 30, 90][period.currentIndex()]
            selected = [
                a
                for a in history
                if not days
                or date.fromisoformat(a["date"]) >= date.today() - timedelta(days=days)
            ]
            m = metrics(selected)
            hl.addWidget(
                QLabel(
                    f"Primeira: {fmt(m['first'])}   Última: {fmt(m['last'])}   Média: {fmt(m['mean'])}\nMelhor: {fmt(m['best'])}   Pior: {fmt(m['worst'])}   Tendência: {m['trend']:+.1f} pp   Meta: {target:.1f}%"
                )
            )
            if m["last"] is not None:
                hl.addWidget(
                    QLabel(f"Distância para a meta: {target - m['last']:+.1f} pp")
                )
            hl.addWidget(Chart(selected, target, self.dark))

        period.currentIndexChanged.connect(draw)
        draw()

    def structure(self, box):
        self.title(
            box,
            "Sessões e submatérias",
            "Crie uma estrutura que acompanhe sua aprendizagem.",
        )
        if not self.selector(box):
            return
        actions = QHBoxLayout()
        box.addLayout(actions)
        tree = QTreeWidget()
        tree.setHeaderLabels(["Estrutura", "Meta", "Tempo / último estudo"])
        box.addWidget(tree)
        nodes = {}
        for session in self.service.data["sessions"]:
            if session["subject_id"] != self.subject_id:
                continue
            node = QTreeWidgetItem([session["title"], "", ""])
            node.setData(0, Qt.UserRole, ("sessions", session))
            tree.addTopLevelItem(node)
            nodes[session["id"]] = node
        for sub in self.service.data["subsessions"]:
            if sub["subject_id"] != self.subject_id:
                continue
            logs = [
                l
                for l in self.service.data["study_logs"]
                if l.get("subsession_id") == sub["id"]
            ]
            hours = sum(l["seconds"] for l in logs) / 3600
            last = max((l["date"] for l in logs), default="—")
            m = metrics(self.service.history(self.subject_id, sub["id"]))
            node = QTreeWidgetItem(
                [
                    sub["title"],
                    f"{fmt(m['last'])} / {sub['target']}%",
                    self.hours(hours * 3600) + " · " + last,
                ]
            )
            node.setData(0, Qt.UserRole, ("subsessions", sub))
            nodes[sub["session_id"]].addChild(node)
        tree.expandAll()
        tree.setMinimumHeight(260)

        def selected():
            item = tree.currentItem()
            if not item:
                raise ValueError("Selecione uma sessão ou subsessão.")
            return item.data(0, Qt.UserRole)

        self.button(
            actions,
            "+ Sessão",
            lambda: self.dialog(
                "Nova sessão",
                [("title", "Título", "text", "")],
                lambda v: self.service.session(self.subject_id, v["title"]),
            ),
        )

        def new_sub():
            sessions = [
                (s["title"], s["id"])
                for s in self.service.data["sessions"]
                if s["subject_id"] == self.subject_id
            ]
            if not sessions:
                raise ValueError("Crie uma sessão primeiro.")
            self.dialog(
                "Nova subsessão",
                [
                    ("session_id", "Sessão", "choice", sessions),
                    ("title", "Título", "text", ""),
                    ("description", "Descrição", "long", ""),
                    ("target", "Meta (%)", "percent", self.subject()["target"]),
                ],
                lambda v: self.service.subsession(self.subject_id, **v),
            )

        self.button(actions, "+ Subsessão", new_sub)

        def edit():
            kind, item = selected()
            fields = [("title", "Título", "text", item["title"])]
            if kind == "subsessions":
                sessions = sorted(
                    [
                        (s["title"], s["id"])
                        for s in self.service.data["sessions"]
                        if s["subject_id"] == self.subject_id
                    ],
                    key=lambda p: p[1] != item["session_id"],
                )
                fields += [
                    ("session_id", "Mover para sessão", "choice", sessions),
                    ("description", "Descrição", "long", item["description"]),
                    ("target", "Meta (%)", "percent", item["target"]),
                ]

            def save(v):
                if not v["title"].strip():
                    raise ValueError("Informe o título.")
                self.service.update(kind, item["id"], **v)

            self.dialog("Editar estrutura", fields, save)

        self.button(actions, "Editar / mover", edit)

        def move(delta):
            kind, item = selected()

            def reorder(d):
                positions = [
                    i
                    for i, x in enumerate(d[kind])
                    if x["subject_id"] == self.subject_id
                    and (kind == "sessions" or x["session_id"] == item["session_id"])
                ]
                current = next(
                    i for i, p in enumerate(positions) if d[kind][p]["id"] == item["id"]
                )
                other = current + delta
                if 0 <= other < len(positions):
                    a, b = positions[current], positions[other]
                    d[kind][a], d[kind][b] = d[kind][b], d[kind][a]

            self.service.mutate(reorder)
            self.refresh()

        self.button(actions, "↑", lambda: move(-1))
        self.button(actions, "↓", lambda: move(1))

        def open_sub():
            kind, sub = selected()
            if kind != "subsessions":
                raise ValueError("Selecione uma subsessão.")
            self.preferred_sub = sub["id"]
            self.nav.setCurrentRow(5)

        self.button(box, "Abrir anotações e gráfico da subsessão", open_sub)
        box.addStretch()
