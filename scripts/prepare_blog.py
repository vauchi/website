#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Prepare hash-bound source dates while Git history is available."""

import hashlib
import json
import sys
from pathlib import Path

from source_dates import last_modified


def prepare(root, check=False):
    blog = root / "blog"
    manifest = blog / "source-dates.json"
    if check:
        data = json.loads(manifest.read_text()) if manifest.exists() else {}
        for relative, entry in data.items():
            source = (blog / "content" / relative).resolve()
            if not source.is_relative_to((blog / "content").resolve()):
                raise ValueError("source outside blog")
            if hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"source changed after date preparation: {relative}")
    else:
        data = {}
        for source in sorted((blog / "content").rglob("*.md")):
            timestamp = last_modified(root, source)
            if timestamp:
                data[source.relative_to(blog / "content").as_posix()] = {
                    "dateModified": timestamp,
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                }
    manifest.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Blog source dates: {len(data)} verified entries")


if __name__ == "__main__":
    arguments = [arg for arg in sys.argv[1:] if arg != "--check"]
    prepare(Path(arguments[0]) if arguments else Path.cwd(), "--check" in sys.argv)
