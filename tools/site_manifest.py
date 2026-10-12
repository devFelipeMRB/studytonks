"""Confirm published GitHub assets before enabling the website installer link."""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = "devFelipeMRB/studytonks"


def manifest_from_release(release):
    result = dict(available=False, version=None, installer_url=None, portable_url=None)
    if (
        not isinstance(release, dict)
        or release.get("draft")
        or release.get("prerelease")
    ):
        return result
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not tag:
        return result
    assets = release.get("assets")
    if not isinstance(assets, list):
        return result
    prefix = f"https://github.com/{REPOSITORY}/releases/download/{urllib.parse.quote(tag, safe='')}/"

    def asset_url(name):
        for asset in assets:
            if (
                isinstance(asset, dict)
                and asset.get("name") == name
                and asset.get("state") == "uploaded"
                and isinstance(asset.get("size"), int)
                and asset["size"] > 0
                and asset.get("browser_download_url") == prefix + name
            ):
                return asset["browser_download_url"]
        return None

    installer = asset_url("Studytonks-Setup.exe")
    if installer:
        result.update(
            available=True,
            version=tag,
            installer_url=installer,
            portable_url=asset_url("Studytonks-Portable.zip"),
        )
    return result


def fetch_release(tag=None):
    suffix = "tags/" + urllib.parse.quote(tag, safe="") if tag else "latest"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/releases/{suffix}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Studytonks-site-build",
        },
    )
    token = os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    parser.add_argument("--output", type=Path, default=Path("site/release.json"))
    args = parser.parse_args()
    result = manifest_from_release(fetch_release(args.tag))
    if args.tag and not result["available"]:
        raise RuntimeError(
            "The tagged installer has not been published; website download remains disabled."
        )
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Website manifest: installer "
        + ("confirmed published" if result["available"] else "in preparation")
    )


if __name__ == "__main__":
    main()
