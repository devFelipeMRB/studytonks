"""Open the real packaged Windows GUI with temporary data and a bounded wait."""

from pathlib import Path
import subprocess
import sys


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("The Windows GUI bundle must be checked on Windows.")
    root = Path(__file__).resolve().parents[1]
    executable = root / "dist" / "Studytonks" / "Studytonks.exe"
    try:
        subprocess.run(
            [str(executable), "--smoke-test"], cwd=root, check=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError) as error:
        sys.exit(f"Packaged GUI failed to open and finish its smoke check: {error}")
    print("Packaged Windows GUI opened and exited successfully.")
