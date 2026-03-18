#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build content manifest and output directory for Vauchi app-files.

Reads source content from app-files-src/, computes checksums, and generates
the manifest.json and output directory structure for deployment.

Content resolution order (per content type):
  1. Sibling repo (local dev: ../themes/, ../locales/)
  2. GitLab API (CI: fetches from main branch)
  3. Committed copy in app-files-src/ (offline fallback)

Usage:
    python scripts/build-manifest.py [--version VERSION] [--output OUTPUT]
"""

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, urlretrieve

GITLAB_API = "https://gitlab.com/api/v4/projects"


def compute_checksum(file_path: Path) -> str:
    """Compute SHA-256 checksum with prefix."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def fetch_gitlab_file(project: str, file_path: str, dest: Path, ref: str = "main") -> bool:
    """Fetch a file from GitLab API. Returns True on success."""
    encoded_project = project.replace("/", "%2F")
    encoded_path = file_path.replace("/", "%2F")
    url = f"{GITLAB_API}/{encoded_project}/repository/files/{encoded_path}/raw?ref={ref}"
    try:
        urlretrieve(url, str(dest))
        return True
    except (URLError, OSError) as e:
        print(f"    GitLab API fetch failed for {file_path}: {e}")
        return False


def list_gitlab_files(project: str, path: str = "", ref: str = "main") -> list[str]:
    """List files in a GitLab repo directory. Returns filenames."""
    encoded_project = project.replace("/", "%2F")
    url = f"{GITLAB_API}/{encoded_project}/repository/tree?ref={ref}&path={path}"
    try:
        data = json.loads(urlopen(url).read())
        return [f["name"] for f in data if f["type"] == "blob"]
    except (URLError, OSError, json.JSONDecodeError):
        return []


def resolve_themes(src_dir: Path, output_dir: Path) -> Path | None:
    """Resolve themes.json: sibling repo → GitLab API → app-files-src/."""
    themes_dest_dir = output_dir / "themes"
    themes_dest = themes_dest_dir / "themes.json"

    # 1. Sibling repo (local dev)
    sibling = src_dir.parent.parent / "themes" / "themes.json"
    if sibling.exists():
        themes_dest_dir.mkdir(exist_ok=True)
        shutil.copy(sibling, themes_dest)
        print(f"  themes: sibling repo ({sibling})")
        return themes_dest

    # 2. GitLab API (CI)
    themes_dest_dir.mkdir(exist_ok=True)
    if fetch_gitlab_file("vauchi/themes", "themes.json", themes_dest):
        print("  themes: GitLab API (vauchi/themes)")
        return themes_dest

    # 3. Committed copy
    local = src_dir / "themes" / "themes.json"
    if local.exists():
        shutil.copy(local, themes_dest)
        print(f"  themes: committed copy ({local})")
        return themes_dest

    print("  themes: NOT FOUND (no sibling, API, or committed copy)")
    themes_dest_dir.rmdir()
    return None


def resolve_locales(src_dir: Path, output_dir: Path) -> Path | None:
    """Resolve locale files: sibling repo → GitLab API → app-files-src/."""
    locales_dest = output_dir / "locales"

    # 1. Sibling repo (local dev)
    sibling = src_dir.parent.parent / "locales"
    if sibling.is_dir() and list(sibling.glob("*.json")):
        locales_dest.mkdir(exist_ok=True)
        for f in sorted(sibling.glob("*.json")):
            if f.name != "locales.schema.json":
                shutil.copy(f, locales_dest / f.name)
        print(f"  locales: sibling repo ({sibling})")
        return locales_dest

    # 2. GitLab API (CI)
    files = list_gitlab_files("vauchi/locales")
    locale_files = [f for f in files if f.endswith(".json") and f != "locales.schema.json"]
    if locale_files:
        locales_dest.mkdir(exist_ok=True)
        fetched = 0
        for name in sorted(locale_files):
            if fetch_gitlab_file("vauchi/locales", name, locales_dest / name):
                fetched += 1
        if fetched > 0:
            print(f"  locales: GitLab API ({fetched} files from vauchi/locales)")
            return locales_dest

    # 3. Committed copy
    local = src_dir / "locales"
    if local.is_dir() and list(local.glob("*.json")):
        locales_dest.mkdir(exist_ok=True)
        for f in sorted(local.glob("*.json")):
            shutil.copy(f, locales_dest / f.name)
        print(f"  locales: committed copy ({local})")
        return locales_dest

    print("  locales: NOT FOUND")
    return None


def build_manifest(
    src_dir: Path, output_dir: Path, version: str, base_url: str
) -> dict:
    """Build the content manifest and copy files to output."""
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "content": {},
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    print("  Resolving content sources...")

    # Process networks.json (always from app-files-src)
    networks_src = src_dir / "networks.json"
    if networks_src.exists():
        networks_dest = output_dir / "networks.json"
        shutil.copy(networks_src, networks_dest)
        manifest["content"]["networks"] = {
            "version": version,
            "path": "networks.json",
            "checksum": compute_checksum(networks_dest),
            "size_bytes": networks_dest.stat().st_size,
            "min_app_version": "0.1.0",
        }

    # Process locales (three-tier resolution)
    locales_dest = resolve_locales(src_dir, output_dir)
    if locales_dest:
        files = {}
        for locale_file in sorted(locales_dest.glob("*.json")):
            lang = locale_file.stem
            files[lang] = {
                "path": locale_file.name,
                "checksum": compute_checksum(locale_file),
                "size_bytes": locale_file.stat().st_size,
            }
        if files:
            manifest["content"]["locales"] = {
                "version": version,
                "path": "locales/",
                "min_app_version": "0.1.0",
                "files": files,
            }

    # Process themes (three-tier resolution)
    themes_dest = resolve_themes(src_dir, output_dir)
    if themes_dest:
        manifest["content"]["themes"] = {
            "version": version,
            "path": "themes/themes.json",
            "checksum": compute_checksum(themes_dest),
            "size_bytes": themes_dest.stat().st_size,
            "min_app_version": "0.1.0",
        }

    # Process help (if exists locally)
    help_src = src_dir / "help"
    if help_src.exists() and help_src.is_dir():
        help_dest = output_dir / "help"
        if help_dest.exists():
            shutil.rmtree(help_dest)
        shutil.copytree(help_src, help_dest)

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Build Vauchi content manifest")
    parser.add_argument(
        "--version", default="1.0.0", help="Content version (default: 1.0.0)"
    )
    parser.add_argument(
        "--output",
        default="public/app-files",
        help="Output directory (default: public/app-files)",
    )
    parser.add_argument(
        "--base-url",
        default="https://vauchi.app/app-files/",
        help="Base URL for content (default: https://vauchi.app/app-files/)",
    )
    parser.add_argument(
        "--src",
        default="app-files-src",
        help="Source directory (default: app-files-src)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    src_dir = root_dir / args.src
    output_dir = root_dir / args.output

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        return 1

    print("Building content manifest...")
    print(f"  Source: {src_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Version: {args.version}")

    if output_dir.exists():
        shutil.rmtree(output_dir)

    manifest = build_manifest(src_dir, output_dir, args.version, args.base_url)

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nGenerated manifest:")
    print(json.dumps(manifest, indent=2))

    print(f"\nOutput files:")
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            rel_path = path.relative_to(output_dir)
            print(f"  {rel_path}")

    return 0


if __name__ == "__main__":
    exit(main())