"""Assemble actual Windows outputs; never fabricate executables on another OS."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import subprocess
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT_FILES = (
    "README.md",
    "main.py",
    "pyproject.toml",
    "build.bat",
    ".gitignore",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-lock.txt",
    "LICENSE",
    "LICENSE.txt",
)
SOURCE_DIRECTORIES = ("app", "tests", "tools", "packaging", "site", "docs", ".github")
SOURCE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".md",
    ".rst",
    ".txt",
    ".toml",
    ".yml",
    ".yaml",
    ".ps1",
    ".bat",
    ".iss",
    ".html",
    ".css",
    ".js",
    ".svg",
    ".png",
    ".ico",
    ".webp",
    ".jpg",
    ".jpeg",
    ".gif",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".webmanifest",
}
EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "build",
    "dist",
    "data",
    "backups",
    "logs",
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_windows_executable(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as stream:
        return stream.read(2) == b"MZ"


def write_source_archive(destination: Path) -> None:
    if (ROOT / ".git").exists() and shutil.which("git"):
        # The tag/revision checked out by Actions is authoritative for releases.
        subprocess.run(
            [
                "git",
                "archive",
                "--format=zip",
                "--prefix=Studytonks-Source/",
                f"--output={destination}",
                "HEAD",
            ],
            cwd=ROOT,
            check=True,
        )
        return

    # A source ZIP has no .git directory and must remain buildable without Git.
    # Include known project sources/assets; never collect arbitrary local files,
    # persistent JSON snapshots, secrets, caches, environments or build outputs.
    files = [ROOT / name for name in SOURCE_ROOT_FILES if (ROOT / name).is_file()]
    for name in SOURCE_DIRECTORIES:
        directory = ROOT / name
        for source in directory.rglob("*"):
            relative = source.relative_to(directory)
            if any(
                part in EXCLUDED_DIRECTORIES or part.startswith(".")
                for part in relative.parts[:-1]
            ):
                continue
            if source.is_symlink() or not source.is_file():
                continue
            if source.name.startswith(".") and source.name != ".nojekyll":
                continue
            if source.suffix.lower() in SOURCE_EXTENSIONS or source.name == ".nojekyll":
                files.append(source)
    with zipfile.ZipFile(
        destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6
    ) as bundle:
        for source in sorted(files):
            if not source.is_symlink():
                bundle.write(
                    source, "Studytonks-Source/" + source.relative_to(ROOT).as_posix()
                )


def assemble(app_only: bool = False) -> list[Path]:
    if sys.platform != "win32":
        raise RuntimeError("Windows release artifacts must be built on Windows.")
    app = ROOT / "dist" / "Studytonks"
    executable = app / "Studytonks.exe"
    if not is_windows_executable(executable):
        raise RuntimeError("Missing actual Windows executable from PyInstaller.")
    if not (app / "_internal").is_dir():
        raise RuntimeError("Missing bundled Python/Qt dependencies (_internal).")
    release = ROOT / "dist" / "release"
    release.mkdir(parents=True, exist_ok=True)
    installer = release / "Studytonks-Setup.exe"
    if not app_only and not is_windows_executable(installer):
        raise RuntimeError("Build the installer with Inno Setup before releasing.")

    archive = release / "Studytonks-Portable.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for source in sorted(app.rglob("*")):
            if source.is_file():
                bundle.write(source, source.relative_to(app.parent).as_posix())
        bundle.write(ROOT / "packaging" / "portable-readme.txt", "LEIA-ME.txt")
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError("Portable archive failed its CRC integrity check.")

    source = release / "Studytonks-Source.zip"
    write_source_archive(source)
    artifacts = [archive, source] if app_only else [installer, archive, source]
    manifest = release / "SHA256SUMS.txt"
    manifest.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in artifacts),
        encoding="utf-8",
    )
    return artifacts + [manifest]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-only", action="store_true")
    arguments = parser.parse_args()
    try:
        paths = assemble(arguments.app_only)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Packaging failed: {error}\n")
    for path in paths:
        print(path.relative_to(ROOT))
