#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decide whether a main commit may deploy landing without the manual step.

Writes `DEPLOY_AUTO=blog-content` to a dotenv file when every change since
the commit production runs (its build-info.json) is blog content or a blog
image, which is what the blog CMS commits; `deploy:trigger` forwards it and
`_private`'s landing deploy runs on its own for that value. Anything else,
and anything the classifier cannot establish, writes an empty value, so the
deploy stays manual (vauchi/private#1249).
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

AUTO_DEPLOY_PATHS = (
    re.compile(r"^blog/content/"),
    re.compile(r"^blog/static/images/"),
)
BLOG_CONTENT = "blog-content"
SHA = re.compile(r"^[0-9a-f]{40}$")


def changed_paths(repo: Path, base: str, head: str):
    """Paths changed between two commits, or None when git cannot say."""
    result = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", f"{base}..{head}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def classify(repo: Path, deployed: str, head: str) -> str:
    """`blog-content` when every change since `deployed` is blog content."""
    if not SHA.match(deployed or "") or deployed == head:
        return ""
    paths = changed_paths(repo, deployed, head)
    if not paths:
        return ""
    if all(any(rule.match(path) for rule in AUTO_DEPLOY_PATHS) for path in paths):
        return BLOG_CONTENT
    return ""


def deployed_sha(build_info_url: str) -> str:
    """The commit production runs, or "" when its build-info cannot be read."""
    try:
        with urllib.request.urlopen(build_info_url, timeout=10) as response:
            return str(json.load(response).get("sha", ""))
    except (OSError, ValueError, AttributeError):
        return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--head", required=True)
    parser.add_argument("--build-info-url", default="https://vauchi.app/build-info.json")
    parser.add_argument("--dotenv", required=True)
    args = parser.parse_args(argv)

    deployed = deployed_sha(args.build_info_url)
    decision = classify(Path(args.repo), deployed, args.head)
    Path(args.dotenv).write_text(f"DEPLOY_AUTO={decision}\n")
    print(
        f"classify-deploy: production runs {deployed[:8] or 'unknown'}, "
        f"head {args.head[:8]}: {decision or 'manual deploy'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
