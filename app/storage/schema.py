"""Strict versioned schema; reject broken/foreign snapshots before any write."""

from __future__ import annotations
from datetime import datetime, date
from uuid import UUID
import math


class StorageError(RuntimeError):
    pass


class UnsupportedSchema(StorageError):
    pass


class RecoveryRequired(StorageError):
    pass


def defaults():
    return {
        "schema_version": 1,
        "settings": {
            "theme": "automatic",
            "default_target": 85,
            "notifications": True,
            "autostart": False,
            "minimized": False,
            "background": False,
            "hours_format": "decimal",
            "backup_days": 1,
            "backup_dir": "",
            "chart_days": 0,
        },
        "subjects": [],
        "sessions": [],
        "subsessions": [],
        "assessments": [],
        "study_logs": [],
        "notes": {},
        "bootcamps": [],
        "reminders": [],
    }


def migrate(data):
    # Version 0 is the documented pre-release format: same entities,
    # settings were partial and notes were bare HTML strings.
    if isinstance(data, dict) and data.get("schema_version") == 0:
        settings, notes = data.get("settings", {}), data.get("notes", {})
        if not isinstance(settings, dict) or not isinstance(notes, dict):
            raise StorageError("Dados legados inválidos. O arquivo original foi preservado.")
        data["settings"] = {**defaults()["settings"], **settings}
        data["notes"] = {
            k: {"format": "html", "text": v, "updated_at": datetime.now().isoformat()}
            if isinstance(v, str)
            else v
            for k, v in notes.items()
        }
        data["schema_version"] = 1
    if (
        isinstance(data, dict)
        and type(data.get("schema_version")) is int
        and data["schema_version"] not in (0, 1)
    ):
        raise UnsupportedSchema(
            "Versão de dados não suportada. Use uma versão compatível do Studytonks; o arquivo foi preservado."
        )
    return validate(data)


def validate(data):
    try:
        _validate(data)
    except (ValueError, TypeError, KeyError, OverflowError, AttributeError) as exc:
        raise StorageError(
            "Dados inválidos. O arquivo original foi preservado."
        ) from exc
    return data


def _validate(data):
    def require(ok):
        if not ok:
            raise ValueError("Invalid schema")

    def text(v, nonempty=False):
        require(isinstance(v, str) and (not nonempty or bool(v.strip())))

    def number(v, low=0, high=float("inf")):
        require(type(v) in (int, float) and math.isfinite(v) and low <= v <= high)

    def boolean(v):
        require(type(v) is bool)

    def iso(v, day=False):
        text(v)
        if day:
            require(date.fromisoformat(v).isoformat() == v)
        else:
            parsed = datetime.fromisoformat(v)
            require(parsed.tzinfo is None)

    require(
        isinstance(data, dict)
        and type(data.get("schema_version")) is int
        and data["schema_version"] == 1
    )
    for key, value in defaults().items():
        require(key in data and isinstance(data[key], type(value)))
    settings = data["settings"]
    require(settings["theme"] in ("automatic", "dark", "light"))
    require(settings["hours_format"] in ("decimal", "clock"))
    number(settings["default_target"], 0, 100)
    number(settings["backup_days"], 0, 365)
    text(settings["backup_dir"])
    require(settings["chart_days"] in (0, 7, 30, 90))
    for key in ("notifications", "autostart", "minimized", "background"):
        boolean(settings[key])
    entities = (
        "subjects",
        "sessions",
        "subsessions",
        "assessments",
        "study_logs",
        "bootcamps",
        "reminders",
    )
    all_ids = set()
    maps = {}
    for key in entities:
        maps[key] = {}
        for item in data[key]:
            require(isinstance(item, dict))
            text(item["id"])
            UUID(item["id"])
            require(item["id"] not in all_ids)
            all_ids.add(item["id"])
            maps[key][item["id"]] = item
            iso(item["created_at"])
    subjects, sessions, subs = maps["subjects"], maps["sessions"], maps["subsessions"]
    for s in subjects.values():
        text(s["name"], True)
        text(s["description"])
        text(s["color"])
        text(s["icon"])
        number(s["target"], 0, 100)
        boolean(s["archived"])

    def links(item):
        sid = item["subject_id"]
        require(sid in subjects)
        if item.get("session_id"):
            require(
                item["session_id"] in sessions
                and sessions[item["session_id"]]["subject_id"] == sid
            )
        if item.get("subsession_id"):
            require(
                item["subsession_id"] in subs
                and subs[item["subsession_id"]]["subject_id"] == sid
            )
            if item.get("session_id"):
                require(subs[item["subsession_id"]]["session_id"] == item["session_id"])

    for s in sessions.values():
        links(s)
        text(s["title"], True)
    for s in subs.values():
        links(s)
        require(s["session_id"] in sessions)
        text(s["title"], True)
        text(s["description"])
        number(s["target"], 0, 100)
    for a in maps["assessments"].values():
        links(a)
        text(a["name"], True)
        iso(a["date"], True)
        number(a["percentage"], 0, 100)
        if "duration" in a:
            number(a["duration"])
        for key in ("observations", "difficulties"):
            if key in a:
                text(a[key])
        number(a["obtained"])
        number(a["maximum"], 0.000000001)
        require(isinstance(a["components"], list))
        component_ids = set()
        require(a["method"] in ("points", "total_points", "weighted_percentages"))
        for c in a["components"]:
            require(isinstance(c, dict))
            require(
                c["subsession_id"] in subs
                and subs[c["subsession_id"]]["subject_id"] == a["subject_id"]
            )
            require(c["subsession_id"] not in component_ids)
            component_ids.add(c["subsession_id"])
            number(c["maximum"], 0.000000001)
            number(c["obtained"], 0, c["maximum"])
            number(c["percentage"], 0, 100)
            require(abs(c["percentage"] - c["obtained"] / c["maximum"] * 100) < 1e-7)
        if a["components"]:
            if a["method"] == "total_points":
                require(
                    all(c.get("mode", "points") == "points" for c in a["components"])
                )
                expected = (
                    sum(c["obtained"] for c in a["components"])
                    / sum(c["maximum"] for c in a["components"])
                    * 100
                )
            else:
                require(a["method"] == "weighted_percentages")
                for c in a["components"]:
                    require(c.get("mode") == "percentage")
                    number(c.get("weight", 1), 0.000000001)
                expected = sum(
                    c["percentage"] * c.get("weight", 1) for c in a["components"]
                ) / sum(c.get("weight", 1) for c in a["components"])
        else:
            require(a["method"] == "points")
            number(a["obtained"], 0, a["maximum"])
            expected = a["obtained"] / a["maximum"] * 100
        require(abs(a["percentage"] - expected) < 1e-7)
    for l in maps["study_logs"].values():
        links(l)
        number(l["seconds"], 0.000000001)
        iso(l["start"])
        iso(l["end"])
        iso(l["date"], True)
        require(
            datetime.fromisoformat(l["end"]) >= datetime.fromisoformat(l["start"])
            and l["date"] == datetime.fromisoformat(l["start"]).date().isoformat()
        )
    for identifier, note in data["notes"].items():
        require(identifier in subs and isinstance(note, dict))
        require(note["format"] == "html")
        text(note["text"])
        iso(note["updated_at"])
    for b in maps["bootcamps"].values():
        links(b)
        text(b["name"], True)
        iso(b["start"], True)
        iso(b["end"], True)
        require(b["start"] <= b["end"])
        number(b["hours"], 0.000000001)
        number(b["target"], 0, 100)
        text(b["plan"])
        require(isinstance(b["sessions"], list))
        require(
            all(
                identifier in sessions
                and sessions[identifier]["subject_id"] == b["subject_id"]
                for identifier in b["sessions"]
            )
        )
        require(
            isinstance(b["days"], list)
            and bool(b["days"])
            and all(type(day) is int and 0 <= day <= 6 for day in b["days"])
        )
        if b.get("final_assessment"):
            require(
                b["final_assessment"] in maps["assessments"]
                and maps["assessments"][b["final_assessment"]]["subject_id"]
                == b["subject_id"]
            )
    for r in maps["reminders"].values():
        text(r["title"], True)
        iso(r["when"])
        boolean(r["enabled"])
        require(r["recurrence"] in ("once", "daily", "weekly"))
        require(
            isinstance(r["days"], list)
            and all(type(day) is int and 0 <= day <= 6 for day in r["days"])
        )
        if r["recurrence"] == "weekly":
            require(bool(r["days"]))
        if r.get("subject_id"):
            links(r)
        else:
            require(not r.get("session_id") and not r.get("subsession_id"))
        if r.get("last_fired"):
            iso(r["last_fired"])

    active = settings.get("active_study")
    if active is not None:
        require(isinstance(active, dict) and isinstance(active["link"], dict))
        links(active["link"])
        number(active["seconds"])
        iso(active["start"])
