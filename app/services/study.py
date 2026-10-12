from __future__ import annotations
import copy
import math
import time
from datetime import datetime, date, timedelta
from uuid import uuid4


def percentage(obtained, maximum):
    obtained, maximum = float(obtained), float(maximum)
    if (
        not math.isfinite(obtained)
        or not math.isfinite(maximum)
        or maximum <= 0
        or not 0 <= obtained <= maximum
    ):
        raise ValueError(
            "A nota deve estar entre zero e a nota máxima, que deve ser positiva."
        )
    return obtained / maximum * 100


def assessment_order(assessment):
    """Order by evaluation date, then entry time for evaluations on the same day."""
    return (
        assessment["date"],
        datetime.fromisoformat(assessment.get("created_at", assessment["date"])),
        assessment["id"],
    )


def metrics(history):
    rows = sorted(history, key=assessment_order)
    scores = [r["percentage"] for r in rows]
    return {
        "count": len(scores),
        "first": scores[0] if scores else None,
        "last": scores[-1] if scores else None,
        "mean": sum(scores) / len(scores) if scores else None,
        "best": max(scores) if scores else None,
        "worst": min(scores) if scores else None,
        "trend": scores[-1] - scores[-2] if len(scores) > 1 else 0,
    }


class StudyService:
    def __init__(self, store):
        self.store = store

    @property
    def data(self):
        return self.store.data

    def mutate(self, operation):
        candidate = copy.deepcopy(self.data)
        result = operation(candidate)
        self.store.commit(candidate)
        return result

    def add(self, collection, **fields):
        item = {"id": str(uuid4()), "created_at": datetime.now().isoformat(), **fields}
        self.mutate(lambda d: d[collection].append(item))
        return item

    def update(self, collection, identifier, **fields):
        def edit(d):
            item = next(x for x in d[collection] if x["id"] == identifier)
            item.update(fields)
            if collection == "subsessions" and "session_id" in fields:
                for key in ("assessments", "study_logs"):
                    for linked in d[key]:
                        if linked.get("subsession_id") == identifier:
                            linked["session_id"] = fields["session_id"]
            active = d["settings"].get("active_study")
            if (
                collection == "subsessions"
                and "session_id" in fields
                and active
                and active["link"].get("subsession_id") == identifier
            ):
                active["link"]["session_id"] = fields["session_id"]
            item["updated_at"] = datetime.now().isoformat()

        self.mutate(edit)

    def subject(self, name, description="", color="#659ED5", icon="📘", target=None):
        if not name.strip():
            raise ValueError("Informe o nome da matéria.")
        return self.add(
            "subjects",
            name=name.strip(),
            description=description,
            color=color,
            icon=icon,
            target=target
            if target is not None
            else self.data["settings"]["default_target"],
            archived=False,
        )

    def session(self, subject_id, title):
        if not title.strip():
            raise ValueError("Informe o título.")
        return self.add("sessions", subject_id=subject_id, title=title.strip())

    def subsession(self, subject_id, session_id, title, description="", target=85):
        if not title.strip():
            raise ValueError("Informe o título.")
        if not any(
            x["id"] == session_id and x["subject_id"] == subject_id
            for x in self.data["sessions"]
        ):
            raise ValueError("Sessão não pertence à matéria.")
        return self.add(
            "subsessions",
            subject_id=subject_id,
            session_id=session_id,
            title=title.strip(),
            description=description,
            target=target,
        )

    def note(self, subsession_id, html):
        self.mutate(
            lambda d: d["notes"].update(
                {
                    subsession_id: {
                        "format": "html",
                        "text": html,
                        "updated_at": datetime.now().isoformat(),
                    }
                }
            )
        )

    def assessment_values(
        self, subject_id, name, on, obtained=0, maximum=100, components=None, **extra
    ):
        if not name.strip():
            raise ValueError("Informe o nome da avaliação.")
        date.fromisoformat(on)
        components = copy.deepcopy(components or [])
        sub_ids = [c["subsession_id"] for c in components]
        if len(sub_ids) != len(set(sub_ids)):
            raise ValueError("Uma subsessão aparece mais de uma vez.")
        for c in components:
            if not any(
                s["id"] == c["subsession_id"] and s["subject_id"] == subject_id
                for s in self.data["subsessions"]
            ):
                raise ValueError("Componente pertence a outra matéria.")
            c["percentage"] = percentage(c["obtained"], c["maximum"])
        if components:
            point_mode = all(c.get("mode", "points") == "points" for c in components)
            if point_mode:
                score = percentage(
                    sum(c["obtained"] for c in components),
                    sum(c["maximum"] for c in components),
                )
                obtained = sum(c["obtained"] for c in components)
                maximum = sum(c["maximum"] for c in components)
                method = "total_points"
            else:
                if any(c.get("mode") != "percentage" for c in components):
                    raise ValueError("Use o mesmo método em todos os componentes.")
                weights = [float(c.get("weight", 1)) for c in components]
                if any(not math.isfinite(w) or w <= 0 for w in weights):
                    raise ValueError("Pesos devem ser positivos.")
                score = sum(
                    c["percentage"] * w for c, w in zip(components, weights)
                ) / sum(weights)
                obtained, maximum = score, 100
                method = "weighted_percentages"
        else:
            score, method = percentage(obtained, maximum), "points"
        if extra.get("subsession_id") and not extra.get("session_id"):
            sub = next(
                x for x in self.data["subsessions"] if x["id"] == extra["subsession_id"]
            )
            extra["session_id"] = sub["session_id"]
        return dict(
            subject_id=subject_id,
            name=name.strip(),
            date=on,
            obtained=obtained,
            maximum=maximum,
            percentage=score,
            components=components,
            method=method,
            **extra,
        )

    def assessment(self, *args, **kwargs):
        return self.add("assessments", **self.assessment_values(*args, **kwargs))

    def edit_assessment(self, identifier, **values):
        calculated = self.assessment_values(**values)

        def edit(d):
            existing = next(x for x in d["assessments"] if x["id"] == identifier)
            if existing["subject_id"] != calculated["subject_id"]:
                for b in d["bootcamps"]:
                    if b.get("final_assessment") == identifier:
                        b["final_assessment"] = None
            existing.update(calculated)
            existing["updated_at"] = datetime.now().isoformat()

        self.mutate(edit)

    def history(self, subject_id, subsession_id=None):
        result = []
        for a in self.data["assessments"]:
            if a["subject_id"] != subject_id:
                continue
            if subsession_id:
                matched = next(
                    (c for c in a["components"] if c["subsession_id"] == subsession_id),
                    None,
                )
                if matched:
                    result.append({**a, "percentage": matched["percentage"]})
                elif not a["components"] and a.get("subsession_id") == subsession_id:
                    result.append(a)
            else:
                result.append(a)
        return sorted(result, key=assessment_order)

    def log(
        self,
        subject_id,
        seconds,
        subsession_id=None,
        session_id=None,
        start=None,
        end=None,
        finish_active=False,
    ):
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("Tempo deve ser positivo.")
        if subsession_id and not session_id:
            sub = next(x for x in self.data["subsessions"] if x["id"] == subsession_id)
            session_id = sub["session_id"]
        now = datetime.now().isoformat()
        if start:
            end = end or (
                datetime.fromisoformat(start) + timedelta(seconds=seconds)
            ).isoformat()
        else:
            end = end or now
            start = (
                datetime.fromisoformat(end) - timedelta(seconds=seconds)
            ).isoformat()
        item = dict(
            id=str(uuid4()),
            created_at=now,
            subject_id=subject_id,
            subsession_id=subsession_id,
            session_id=session_id,
            seconds=seconds,
            start=start,
            end=end,
            date=start[:10],
        )

        def save(d):
            d["study_logs"].append(item)
            if finish_active:
                d["settings"]["active_study"] = None

        self.mutate(save)
        return item

    def save_active_study(self, link, seconds, start):
        link = dict(link)
        if link.get("subsession_id"):
            sub = next(
                x for x in self.data["subsessions"] if x["id"] == link["subsession_id"]
            )
            link["session_id"] = sub["session_id"]
        active = dict(link=link, seconds=seconds, start=start)
        self.settings(active_study=active)
        return active

    def delete(self, collection, identifier):
        def remove(d):
            if collection == "subjects":
                active = d["settings"].get("active_study")
                if active and active["link"]["subject_id"] == identifier:
                    raise ValueError(
                        "Encerre a sessão de estudo antes de excluir esta matéria."
                    )
                subs = {
                    x["id"] for x in d["subsessions"] if x["subject_id"] == identifier
                }
                for key in (
                    "sessions",
                    "subsessions",
                    "assessments",
                    "study_logs",
                    "bootcamps",
                    "reminders",
                ):
                    d[key] = [x for x in d[key] if x.get("subject_id") != identifier]
                d["notes"] = {k: v for k, v in d["notes"].items() if k not in subs}
            if collection == "assessments":
                for b in d["bootcamps"]:
                    if b.get("final_assessment") == identifier:
                        b["final_assessment"] = None
            d[collection] = [x for x in d[collection] if x["id"] != identifier]

        self.mutate(remove)

    def settings(self, **values):
        self.mutate(lambda d: d["settings"].update(values))

    def bootcamp_status(self, bootcamp):
        seconds = sum(
            l["seconds"]
            for l in self.data["study_logs"]
            if l["subject_id"] == bootcamp["subject_id"]
            and bootcamp["start"] <= l["date"] <= bootcamp["end"]
            and (
                not bootcamp["sessions"] or l.get("session_id") in bootcamp["sessions"]
            )
            and date.fromisoformat(l["date"]).weekday()
            in bootcamp.get("days", range(7))
        )
        final = next(
            (
                a
                for a in self.data["assessments"]
                if a["id"] == bootcamp.get("final_assessment")
            ),
            None,
        )
        return min(100, seconds / (bootcamp["hours"] * 3600) * 100), bool(
            final
            and bootcamp["start"] <= final["date"] <= bootcamp["end"]
            and final["percentage"] >= bootcamp["target"]
        )


class StudyTimer:
    def __init__(self, clock=time.monotonic):
        self.clock, self.elapsed, self.since, self.start = clock, 0.0, None, None

    def resume(self):
        if self.since is None:
            self.since = self.clock()
            if self.start is None:
                self.start = datetime.now().isoformat()

    def pause(self):
        if self.since is not None:
            self.elapsed += self.clock() - self.since
            self.since = None

    def seconds(self):
        return self.elapsed + (
            self.clock() - self.since if self.since is not None else 0
        )

    def finish(self):
        self.pause()
        return self.elapsed
