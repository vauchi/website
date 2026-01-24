#!/usr/bin/env python3
"""Build content manifest and output directory for Vauchi app-files.

Reads source content from app-files-src/, computes checksums, and generates
the manifest.json and output directory structure for deployment.

Usage:
    python scripts/build-manifest.py [--version VERSION] [--output OUTPUT]
"""

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def compute_checksum(file_path: Path) -> str:
    """Compute SHA-256 checksum with prefix."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


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

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process networks.json
    networks_src = src_dir / "networks.json"
    if networks_src.exists():
        networks_dest = output_dir / "networks.json"
        shutil.copy(networks_src, networks_dest)
        manifest["content"]["networks"] = {
            "version": version,
            "path": "networks.json",
            "checksum": compute_checksum(networks_dest),
            "min_app_version": "0.1.0",
        }

    # Process locales
    locales_src = src_dir / "locales"
    if locales_src.exists() and locales_src.is_dir():
        locales_dest = output_dir / "locales"
        locales_dest.mkdir(exist_ok=True)

        files = {}
        for locale_file in sorted(locales_src.glob("*.json")):
            lang = locale_file.stem
            dest_file = locales_dest / locale_file.name
            shutil.copy(locale_file, dest_file)
            files[lang] = {
                "path": locale_file.name,
                "checksum": compute_checksum(dest_file),
            }

        if files:
            manifest["content"]["locales"] = {
                "version": version,
                "path": "locales/",
                "min_app_version": "0.1.0",
                "files": files,
            }

    # Process themes
    themes_src = src_dir / "themes" / "themes.json"
    if themes_src.exists():
        themes_dest_dir = output_dir / "themes"
        themes_dest_dir.mkdir(exist_ok=True)
        themes_dest = themes_dest_dir / "themes.json"
        shutil.copy(themes_src, themes_dest)
        manifest["content"]["themes"] = {
            "version": version,
            "path": "themes/themes.json",
            "checksum": compute_checksum(themes_dest),
            "min_app_version": "0.1.0",
        }

    # Process help (if exists)
    help_src = src_dir / "help"
    if help_src.exists() and help_src.is_dir():
        help_dest = output_dir / "help"
        if help_dest.exists():
            shutil.rmtree(help_dest)
        shutil.copytree(help_src, help_dest)
        # Help is typically a directory with multiple files
        # For now, we skip individual checksums

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

    # Get paths relative to script location
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    src_dir = root_dir / args.src
    output_dir = root_dir / args.output

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        return 1

    print(f"Building content manifest...")
    print(f"  Source: {src_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Version: {args.version}")

    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)

    manifest = build_manifest(src_dir, output_dir, args.version, args.base_url)

    # Write manifest
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
