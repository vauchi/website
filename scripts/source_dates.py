# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Return source-file history, never a checkout or build timestamp."""

import subprocess
from datetime import datetime
from pathlib import Path


def last_modified(root, path):
    root, path = root.resolve(), path.resolve()
    if not path.is_relative_to(root):
        return None

    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    try:
        if Path(git("rev-parse", "--show-toplevel")).resolve() != root:
            return None
        relative = path.relative_to(root).as_posix()
        git("ls-files", "--error-unmatch", "--", relative)
        if git("status", "--porcelain", "--", relative):
            return None
        change = git("log", "-1", "--follow", "--format=%H %cI", "--", relative)
        if not change:
            return None
        commit, timestamp = change.split(" ", 1)
        shallow = Path(git("rev-parse", "--git-path", "shallow"))
        if not shallow.is_absolute():
            shallow = root / shallow
        if shallow.is_file() and commit in shallow.read_text().splitlines():
            return None
        return datetime.fromisoformat(timestamp).isoformat()
    except (OSError, subprocess.CalledProcessError):
        return None
