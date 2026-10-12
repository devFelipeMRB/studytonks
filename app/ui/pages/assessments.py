from __future__ import annotations
from datetime import date
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from app.ui.widgets import Form


def fmt(value):
    return "—" if value is None else f"{value:.1f}%"


class AssessmentPages:
    def assessments_page(self, box):
        self.title(
            box,
            "Avaliações",
            "Registre provas realizadas fora do aplicativo. Cada prova conta uma única vez.",
        )
        if not self.selector(box):
            return
        self.button(box, "+ Registrar avaliação", self.new_assessment)
        items = self.service.history(self.subject_id)
        table = self.table(
            box,
            ["Data", "Avaliação", "Nota", "Método", "Dificuldades"],
            [
                [
                    a["date"],
                    a["name"],
                    fmt(a["percentage"]),
                    {
                        "total_points": "Pontos totais",
                        "weighted_percentages": "Média ponderada",
                        "points": "Nota / máxima",
                    }[a["method"]],
                    a.get("difficulties", ""),
                ]
                for a in items
            ],
        )
        actions = QHBoxLayout()
        box.addLayout(actions)
        self.button(
            actions,
            "Editar selecionada",
            lambda: self.new_assessment(self.selected(table, items)),
        )

        def remove():
            a = self.selected(table, items)
            if self.confirm("Remover esta avaliação e seus componentes?"):
                self.service.delete("assessments", a["id"])
                self.refresh()

        self.button(actions, "Remover selecionada", remove)
        box.addStretch()

    def new_assessment(self, existing=None):
        if not self.subject_choices():
            raise ValueError("Crie uma matéria primeiro.")
        a = existing or {}
        today = date.today().isoformat()
        subjects = sorted(
            self.subject_choices(),
            key=lambda x: x[1] != a.get("subject_id", self.subject_id),
        )
        fields = [
            ("subject_id", "Matéria", "choice", subjects),
            ("name", "Nome da avaliação", "text", a.get("name", "")),
            ("date", "Data", "date", a.get("date", today)),
            (
                "mode",
                "Entrada",
                "choice",
                [
                    ("Pontos obtidos / máximos", "points"),
                    ("Porcentagem direta", "percentage"),
                ],
            ),
            ("obtained", "Nota obtida ou porcentagem", "number", a.get("obtained", 0)),
            ("maximum", "Nota máxima (ignorada em %)", "number", a.get("maximum", 100)),
            ("duration", "Duração (minutos, opcional)", "number", a.get("duration", 0)),
            ("observations", "Observações", "long", a.get("observations", "")),
            (
                "difficulties",
                "Assuntos com dificuldade",
                "long",
                a.get("difficulties", ""),
            ),
        ]
        form = Form(self, "Registrar avaliação", fields)
        target_box = QComboBox()
        session_box = QComboBox()
        form.layout.insertRow(1, "Sessão opcional", session_box)
        form.layout.insertRow(2, "Subsessão opcional", target_box)
        components = [] if not existing else [dict(c) for c in a.get("components", [])]
        component_label = QLabel()
        component_label.setWordWrap(True)
        form.layout.insertRow(3, "Componentes da prova", component_label)
        component_buttons = QWidget()
        buttons = QHBoxLayout(component_buttons)
        form.layout.insertRow(4, component_buttons)
        hint = QLabel()
        form.layout.insertRow(5, "Resultado calculado", hint)

        def sync_components():
            names = {s["id"]: s["title"] for s in self.service.data["subsessions"]}
            component_label.setText(
                "\n".join(
                    f"{names.get(c['subsession_id'], '?')}: {c['obtained']}/{c['maximum']} · peso {c.get('weight', 1)}"
                    for c in components
                )
                or "Sem componentes — use a nota geral ou adicione subsessões."
            )
            from app.services.study import percentage

            try:
                if components:
                    if all(c["mode"] == "points" for c in components):
                        score = percentage(
                            sum(c["obtained"] for c in components),
                            sum(c["maximum"] for c in components),
                        )
                        method = "soma dos pontos / soma dos máximos"
                    else:
                        score = sum(
                            percentage(c["obtained"], c["maximum"]) * c["weight"]
                            for c in components
                        ) / sum(c["weight"] for c in components)
                        method = "média das porcentagens ponderada pelos pesos"
                else:
                    score = percentage(
                        form.widgets["obtained"].value(),
                        100
                        if form.widgets["mode"].currentData() == "percentage"
                        else form.widgets["maximum"].value(),
                    )
                    method = "nota geral"
                hint.setText(f"{score:.2f}% · {method}")
            except ValueError:
                hint.setText("Informe uma nota válida.")

        def load_sessions():
            subject_id = form.widgets["subject_id"].currentData()
            session_box.clear()
            session_box.addItem("Nenhuma", None)
            for s in self.service.data["sessions"]:
                if s["subject_id"] == subject_id:
                    session_box.addItem(s["title"], s["id"])
            load_subs()

        def load_subs():
            target_box.clear()
            target_box.addItem("Nenhuma", None)
            for s in self.service.data["subsessions"]:
                if s["subject_id"] == form.widgets["subject_id"].currentData() and (
                    not session_box.currentData()
                    or s["session_id"] == session_box.currentData()
                ):
                    target_box.addItem(s["title"], s["id"])

        def changed_subject():
            components.clear()
            load_sessions()
            sync_components()

        form.widgets["subject_id"].currentIndexChanged.connect(changed_subject)
        session_box.currentIndexChanged.connect(load_subs)
        load_sessions()
        if a.get("session_id"):
            session_box.setCurrentIndex(session_box.findData(a["session_id"]))
        if a.get("subsession_id"):
            target_box.setCurrentIndex(target_box.findData(a["subsession_id"]))

        def add_component():
            subs = [
                (s["title"], s["id"])
                for s in self.service.data["subsessions"]
                if s["subject_id"] == form.widgets["subject_id"].currentData()
                and s["id"] not in {c["subsession_id"] for c in components}
            ]
            if not subs:
                raise ValueError("Crie subsessões ou remova componentes repetidos.")
            f = Form(
                form,
                "Resultado da subsessão",
                [
                    ("subsession_id", "Subsessão", "choice", subs),
                    (
                        "mode",
                        "Método",
                        "choice",
                        [("Pontos", "points"), ("Porcentagem ponderada", "percentage")],
                    ),
                    ("obtained", "Nota obtida ou %", "number", 0),
                    ("maximum", "Nota máxima", "number", 100),
                    ("weight", "Peso (modo porcentagem)", "number", 1),
                ],
            )
            if f.exec() == Form.Accepted:
                v = f.values()
                from app.services.study import percentage

                if v["mode"] == "percentage":
                    v["maximum"] = 100
                percentage(v["obtained"], v["maximum"])
                if v["weight"] <= 0:
                    raise ValueError("Peso deve ser positivo.")
                if components and v["mode"] != components[0]["mode"]:
                    raise ValueError("Todos os componentes devem usar o mesmo método.")
                components.append(v)
                sync_components()

        self.button(buttons, "+ Componente", add_component)
        self.button(
            buttons,
            "Limpar componentes",
            lambda: (components.clear(), sync_components()),
        )
        form.widgets["obtained"].valueChanged.connect(sync_components)
        form.widgets["maximum"].valueChanged.connect(sync_components)
        form.widgets["mode"].currentIndexChanged.connect(sync_components)
        sync_components()

        def save(v):
            v["on"] = v.pop("date")
            mode = v.pop("mode")
            if mode == "percentage":
                v["maximum"] = 100
            v["session_id"] = session_box.currentData()
            v["subsession_id"] = target_box.currentData()
            if components:
                v["subsession_id"] = None
            v["components"] = components
            if existing:
                self.service.edit_assessment(existing["id"], **v)
            else:
                self.service.assessment(**v)

        form.on_submit = save
        if form.exec() == Form.Accepted:
            self.refresh()
