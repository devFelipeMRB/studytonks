"""Verify a Windows bundle includes Python, Qt and the imported VC++ runtimes."""

from __future__ import annotations

from pathlib import Path
import re
import sys


def verify() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Run the bundle runtime check on Windows.")
    import pefile

    app = Path(__file__).resolve().parents[1] / "dist" / "Studytonks"
    internal = app / "_internal"
    files = [path for path in app.rglob("*") if path.is_file()]
    included = {path.name.lower() for path in files}
    required = {
        "python312.dll",
        "qt6core.dll",
        "qt6gui.dll",
        "qt6widgets.dll",
        "qwindows.dll",
        "msvcp140.dll",
        "vcruntime140.dll",
    }
    runtime = re.compile(
        r"^(?:msvcp|vcruntime|concrt|vcomp|vccorlib)\d+(?:_[a-z0-9]+)*\.dll$"
    )
    if not internal.is_dir():
        raise RuntimeError("The PyInstaller dependency directory is missing.")

    # Detect additional VC++ DLLs needed by the exact Qt/numpy binaries bundled.
    for path in files:
        if path.suffix.lower() not in {".exe", ".dll", ".pyd"}:
            continue
        with pefile.PE(str(path), fast_load=True) as executable:
            executable.parse_data_directories(
                directories=[
                    pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                    pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
                ]
            )
            for attribute in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
                for entry in getattr(executable, attribute, []):
                    name = entry.dll.decode("ascii").lower()
                    if runtime.fullmatch(name):
                        required.add(name)
            if (
                path.name == "Studytonks.exe"
                and executable.FILE_HEADER.Machine != 0x8664
            ):
                raise RuntimeError(
                    "Studytonks.exe must be an actual Windows x64 binary."
                )

    missing = required - included
    if missing:
        raise RuntimeError(
            "Missing bundled runtime dependencies: " + ", ".join(sorted(missing))
        )
    print("Bundled Python, Qt platform plugin and VC++ runtime DLLs verified.")


if __name__ == "__main__":
    try:
        verify()
    except (OSError, RuntimeError) as error:
        sys.exit(f"Runtime check failed: {error}")
