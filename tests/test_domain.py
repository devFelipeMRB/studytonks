from datetime import datetime, timedelta
import json
import zipfile
import pytest
from app.storage.store import Store, StorageError
from app.services.study import percentage, metrics, StudyTimer, StudyService
from app.services.reminders import occurrence


def test_create_edit_archive_subject(service):
    s = service.subject("Python", description="programação")
    service.update("subjects", s["id"], name="Python avançado", archived=True)
    assert service.data["subjects"][0]["name"] == "Python avançado"
    assert service.data["subjects"][0]["archived"]


def test_hierarchy_notes(service, hierarchy):
    s, session, sub = hierarchy
    text = "<h1>Limites</h1><p>α &amp; β \\frac{1}{2}</p><pre>print(1)</pre>"
    service.note(sub["id"], text)
    assert service.data["notes"][sub["id"]]["text"] == text
    assert sub["session_id"] == session["id"]
    service.update("subsessions", sub["id"], title="Continuidade", target=90)
    assert service.data["subsessions"][0]["target"] == 90


@pytest.mark.parametrize(
    "obtained,maximum,result", [(18, 20, 90), (0, 20, 0), (20, 20, 100), (7.5, 10, 75)]
)
def test_percentage(obtained, maximum, result):
    assert percentage(obtained, maximum) == result


@pytest.mark.parametrize(
    "obtained,maximum",
    [(1, 0), (-1, 20), (21, 20), (float("nan"), 20), (1, float("inf"))],
)
def test_invalid_percentage(obtained, maximum):
    with pytest.raises(ValueError):
        percentage(obtained, maximum)


def test_assessment_mean_trend_chronology(service, hierarchy):
    s, _, _ = hierarchy
    service.assessment(s["id"], "Final", "2026-01-03", 18, 20)
    service.assessment(s["id"], "Inicial", "2026-01-01", 40, 100)
    service.assessment(s["id"], "Revisão", "2026-01-02", 80, 100)
    result = metrics(service.history(s["id"]))
    assert result == {
        "count": 3,
        "first": 40,
        "last": 90,
        "mean": 70,
        "best": 90,
        "worst": 40,
        "trend": 10,
    }


def test_multiple_components_no_double_count(service, hierarchy):
    s, session, sub = hierarchy
    other = service.subsession(s["id"], session["id"], "Limites diretos")
    untouched = service.subsession(s["id"], session["id"], "Não avaliada")
    a = service.assessment(
        s["id"],
        "Prova",
        "2026-01-01",
        components=[
            {"subsession_id": sub["id"], "obtained": 9, "maximum": 10},
            {"subsession_id": other["id"], "obtained": 15, "maximum": 20},
        ],
    )
    assert a["percentage"] == 80
    assert metrics(service.history(s["id"]))["count"] == 1
    assert service.history(s["id"], sub["id"])[0]["percentage"] == 90
    assert not service.history(s["id"], untouched["id"])


def test_weighted_components(service, hierarchy):
    s, session, sub = hierarchy
    other = service.subsession(s["id"], session["id"], "Outro")
    a = service.assessment(
        s["id"],
        "Prova",
        "2026-01-01",
        components=[
            {
                "subsession_id": sub["id"],
                "obtained": 90,
                "maximum": 100,
                "mode": "percentage",
                "weight": 3,
            },
            {
                "subsession_id": other["id"],
                "obtained": 50,
                "maximum": 100,
                "mode": "percentage",
                "weight": 1,
            },
        ],
    )
    assert a["percentage"] == 80 and a["method"] == "weighted_percentages"


def test_duplicate_components_rejected(service, hierarchy):
    s, _, sub = hierarchy
    c = {"subsession_id": sub["id"], "obtained": 10, "maximum": 20}
    with pytest.raises(ValueError):
        service.assessment(
            s["id"], "Prova", "2026-01-01", components=[dict(c), dict(c)]
        )
    assert not service.data["assessments"]


def test_timer_excludes_pauses(service, hierarchy):
    clock = [0]
    timer = StudyTimer(lambda: clock[0])
    timer.resume()
    clock[0] = 10
    timer.pause()
    clock[0] = 100
    timer.resume()
    clock[0] = 125
    assert timer.finish() == 35
    s, session, sub = hierarchy
    service.log(s["id"], timer.elapsed, sub["id"], session["id"], timer.start)
    assert service.data["study_logs"][0]["seconds"] == 35


def test_reopen_persistence(service, hierarchy):
    s, session, sub = hierarchy
    service.note(sub["id"], "Texto íntegro 🦉")
    service.assessment(s["id"], "Avaliação", "2026-01-01", 85, 100)
    service.log(s["id"], 1800, sub["id"], session["id"])
    root = service.store.root
    expected = service.data
    service.store.close()
    reopened = Store(root)
    assert reopened.data == expected
    reopened.close()


def test_lock_prevents_multiple_instances(service):
    with pytest.raises(StorageError):
        Store(service.store.root)


def test_backup_restore(service, hierarchy, tmp_path):
    backup = service.store.backup(tmp_path / "backup.zip")
    expected = json.loads(json.dumps(service.data))
    service.subject("Mais uma")
    service.store.restore(backup)
    assert service.data == expected
    assert list((service.store.root / "backups").glob("manual-*.zip"))


def test_reject_unsafe_backup(service, tmp_path):
    path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../state.json", "{}")
    expected = service.data
    with pytest.raises(StorageError):
        service.store.restore(path)
    assert service.data == expected


def test_corrupt_backup_preserves_data(service, tmp_path):
    path = tmp_path / "invalid.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("state.json", '{"schema_version":1}')
    with pytest.raises(StorageError):
        service.store.restore(path)
    assert service.data["subjects"] == []


def test_corruption_recovery(service, hierarchy):
    service.note(hierarchy[2]["id"], "Primeira nota")
    expected = json.loads((service.store.root / "state.previous.json").read_text())
    root = service.store.root
    service.store.close()
    (root / "state.json").write_text("{broken")
    restored = Store(root)
    assert restored.recovered and restored.data == expected
    assert list(root.glob("corrupt-*.json"))
    restored.close()


def test_corruption_without_valid_copy_preserves_original(tmp_path, qapp):
    root = tmp_path / "broken"
    root.mkdir()
    (root / "state.json").write_text("broken")
    with pytest.raises(StorageError):
        Store(root)
    assert (root / "state.json").read_text() == "broken"


def test_subject_delete_cascades(service, hierarchy):
    s, _, sub = hierarchy
    service.note(sub["id"], "A")
    service.log(s["id"], 60)
    service.delete("subjects", s["id"])
    assert (
        not service.data["notes"]
        and not service.data["subsessions"]
        and not service.data["study_logs"]
    )


@pytest.mark.parametrize(
    "recurrence,days,weekday,expected",
    [
        ("once", [], 0, True),
        ("daily", [], 1, True),
        ("weekly", [0], 0, True),
        ("weekly", [0], 1, False),
    ],
)
def test_reminders(recurrence, days, weekday, expected):
    base = datetime(2026, 1, 5, 8, 0)
    now = base + timedelta(days=weekday, seconds=30)
    if recurrence == "once":
        now = base + timedelta(seconds=30)
    reminder = {
        "when": base.isoformat(),
        "recurrence": recurrence,
        "days": days,
        "enabled": True,
    }
    token = occurrence(reminder, now)
    assert bool(token) == expected
    if token:
        reminder["last_fired"] = token
        assert occurrence(reminder, now) is None


def test_bootcamp_approval_and_hours(service, hierarchy):
    s, session, _ = hierarchy
    service.log(s["id"], 3600, session_id=session["id"], start="2026-01-05T10:00:00")
    a = service.assessment(s["id"], "Final", "2026-01-06", 90, 100)
    bootcamp = {
        "subject_id": s["id"],
        "start": "2026-01-05",
        "end": "2026-01-11",
        "hours": 2,
        "target": 85,
        "sessions": [session["id"]],
        "final_assessment": a["id"],
    }
    assert service.bootcamp_status(bootcamp) == (50, True)


def test_move_subsession_preserves_linked_records(service, hierarchy):
    s, old, sub = hierarchy
    service.assessment(
        s["id"],
        "Prova",
        "2026-01-01",
        90,
        100,
        session_id=old["id"],
        subsession_id=sub["id"],
    )
    service.log(s["id"], 60, sub["id"], old["id"])
    new = service.session(s["id"], "Nova organização")
    service.update("subsessions", sub["id"], session_id=new["id"])
    assert service.data["assessments"][0]["session_id"] == new["id"]
    assert service.data["study_logs"][0]["session_id"] == new["id"]


def test_edit_assessment_no_duplicate(service, hierarchy):
    s, _, _ = hierarchy
    a = service.assessment(s["id"], "Prova", "2026-01-01", 18, 20)
    service.edit_assessment(
        a["id"],
        subject_id=s["id"],
        name="Revisada",
        on="2026-01-02",
        obtained=15,
        maximum=20,
    )
    assert metrics(service.history(s["id"]))["count"] == 1
    assert metrics(service.history(s["id"]))["mean"] == 75


def test_schema_migration(service, hierarchy):
    import copy

    root = service.store.root
    legacy = copy.deepcopy(service.data)
    legacy["schema_version"] = 0
    legacy["settings"] = {"theme": "light"}
    legacy["notes"] = {hierarchy[2]["id"]: "<p>Texto legado</p>"}
    service.store.close()
    (root / "state.json").write_text(json.dumps(legacy))
    migrated = Store(root)
    assert migrated.data["schema_version"] == 1
    assert migrated.data["notes"][hierarchy[2]["id"]]["text"] == "<p>Texto legado</p>"
    assert (root / "state.pre-migration.json").exists()
    migrated.close()


def test_reject_inconsistent_backup_scores(service, hierarchy, tmp_path):
    import copy

    s, _, _ = hierarchy
    service.assessment(s["id"], "Prova", "2026-01-01", 18, 20)
    payload = copy.deepcopy(service.data)
    payload["assessments"][0]["percentage"] = 95
    path = tmp_path / "inconsistent.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("state.json", json.dumps(payload))
    with pytest.raises(StorageError):
        service.store.restore(path)
    assert service.history(s["id"])[0]["percentage"] == 90


def test_failed_write_preserves_last_snapshot(service, hierarchy, monkeypatch):
    old = json.loads(service.store.path.read_text())

    def fail(_):
        raise OSError("Simulated disk failure")

    monkeypatch.setattr(service.store, "_atomic", fail)
    with pytest.raises(OSError):
        service.subject("Não deve ser gravada")
    assert service.data == old and json.loads(service.store.path.read_text()) == old


def test_restore_corrupt_startup_from_zip(service, hierarchy, tmp_path):
    source = service.store.backup(tmp_path / "valid.zip")
    expected = service.data
    root = service.store.root
    service.store.close()
    (root / "state.json").write_text("broken")
    (root / "state.previous.json").write_text("also broken")
    recovered = Store(root, recovery_source=source)
    assert recovered.data == expected and recovered.recovered
    assert list(root.glob("corrupt-*.json"))
    recovered.close()


def test_subsession_log_infers_session(service, hierarchy):
    s, session, sub = hierarchy
    service.log(s["id"], 120, sub["id"])
    assert service.data["study_logs"][0]["session_id"] == session["id"]


def test_future_schema_never_downgraded(service, hierarchy):
    root = service.store.root
    service.store.close()
    payload = json.loads((root / "state.json").read_text())
    payload["schema_version"] = 42
    original = json.dumps(payload)
    (root / "state.json").write_text(original)
    with pytest.raises(StorageError):
        Store(root)
    assert (root / "state.json").read_text() == original


def test_active_timer_checkpoint_reopens_and_finishes_once(service, hierarchy):
    s, session, sub = hierarchy
    service.save_active_study(
        {"subject_id": s["id"], "subsession_id": sub["id"], "session_id": None},
        125,
        "2026-01-01T10:00:00",
    )
    root = service.store.root
    service.store.close()
    reopened = Store(root)
    current = StudyService(reopened)
    active = current.data["settings"]["active_study"]
    assert active["seconds"] == 125 and active["link"]["session_id"] == session["id"]
    current.log(
        **active["link"],
        seconds=active["seconds"],
        start=active["start"],
        end="2026-01-01T10:10:00",
        finish_active=True,
    )
    assert (
        current.data["settings"]["active_study"] is None
        and len(current.data["study_logs"]) == 1
    )
    reopened.close()


def test_delete_active_subject_requires_finished_timer(service, hierarchy):
    s, session, _ = hierarchy
    service.save_active_study(
        {"subject_id": s["id"], "session_id": session["id"], "subsession_id": None},
        1,
        "2026-01-01T10:00:00",
    )
    with pytest.raises(ValueError):
        service.delete("subjects", s["id"])
    assert service.data["subjects"]


def test_reminder_occurrence_persists_across_restart(service, hierarchy):
    reminder = service.add(
        "reminders",
        title="Estudar",
        when="2026-01-05T08:00",
        recurrence="daily",
        days=[],
        enabled=True,
        subject_id=hierarchy[0]["id"],
        session_id=None,
        last_fired=None,
    )
    now = datetime(2026, 1, 5, 8, 0, 30)
    token = occurrence(reminder, now)
    service.update("reminders", reminder["id"], last_fired=token)
    root = service.store.root
    service.store.close()
    reopened = Store(root)
    assert occurrence(reopened.data["reminders"][0], now) is None
    reopened.close()


def test_windows_autostart_scopes_and_quotes_own_entry(monkeypatch):
    import sys
    from types import SimpleNamespace
    from app.services.reminders import set_autostart, autostart_status

    entries = {"AnotherApp": "preserve"}

    class Key:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def delete(key, name):
        if name not in entries:
            raise FileNotFoundError
        del entries[name]

    def query(key, name):
        if name not in entries:
            raise FileNotFoundError
        return entries[name], 1

    fake = SimpleNamespace(
        HKEY_CURRENT_USER=1,
        REG_SZ=1,
        CreateKey=lambda hive, path: Key(),
        OpenKey=lambda hive, path: Key(),
        SetValueEx=lambda key, name, reserved, kind, value: entries.update(
            {name: value}
        ),
        DeleteValue=delete,
        QueryValueEx=query,
    )
    with monkeypatch.context() as patch:
        patch.setattr(sys, "platform", "win32")
        patch.setitem(sys.modules, "winreg", fake)
        exe = r"C:\Program Files\Studytonks\Studytonks.exe"
        set_autostart(True, exe)
        assert entries["Studytonks"] == f'"{exe}"' and autostart_status(exe)
        set_autostart(False, exe)
        assert entries == {"AnotherApp": "preserve"}


def test_invalid_zip_reports_storage_error_without_modification(service, tmp_path):
    path = tmp_path / "not-a-zip.zip"
    path.write_bytes(b"not a zip")
    original = service.store.path.read_bytes()
    with pytest.raises(StorageError):
        service.store.restore(path)
    assert service.store.path.read_bytes() == original
