from datetime import datetime


def occurrence(reminder, now):
    if not reminder.get("enabled", True):
        return None
    when = datetime.fromisoformat(reminder["when"])
    recurrence = reminder["recurrence"]
    if now < when:
        return None
    if recurrence == "once":
        candidate = when
    else:
        candidate = datetime.combine(now.date(), when.time())
        if candidate > now:
            return None
        if recurrence == "weekly" and now.weekday() not in reminder["days"]:
            return None
    token = candidate.isoformat()
    if reminder.get("last_fired") == token:
        return None
    # No flood of stale notifications after opening days later.
    if (now - candidate).total_seconds() > 120:
        return None
    return token


def set_autostart(enabled, executable, script=None):
    import sys

    if sys.platform != "win32":
        if enabled:
            raise RuntimeError(
                "Inicialização automática está disponível apenas no Windows."
            )
        return
    import winreg

    command = f'"{executable}"' + (f' "{script}"' if script else "")
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"
    ) as key:
        if enabled:
            winreg.SetValueEx(key, "Studytonks", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "Studytonks")
            except FileNotFoundError:
                pass


def autostart_status(executable, script=None):
    import sys

    if sys.platform != "win32":
        return False
    import winreg

    expected = f'"{executable}"' + (f' "{script}"' if script else "")
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"
        ) as key:
            actual, _ = winreg.QueryValueEx(key, "Studytonks")
            return actual == expected
    except FileNotFoundError:
        return False
