#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the landing deploy classifier (vauchi/private#1249).

A merge whose every change since the deployed commit is blog content may
deploy landing without the manual step; anything else, and anything the
classifier cannot establish, keeps the manual step. Real git repositories
in a temp directory stand in for the checkout; nothing is stubbed.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from scriptloader import load

classifier = load("classify-deploy.py")


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.commit({"index.html": "<p>landing</p>\n"}, "landing")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, files: dict, message: str) -> str:
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            self.git("add", name)
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")


class ClassifyDeployTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self.tmp.name))
        self.deployed = self.repo.git("rev-parse", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def classify(self, head: str, deployed=None) -> str:
        return classifier.classify(
            self.repo.root, self.deployed if deployed is None else deployed, head
        )

    def test_a_post_edit_deploys_without_the_manual_step(self):
        head = self.repo.commit({"blog/content/a-post.md": "+++\n+++\nText\n"}, "post")
        self.assertEqual(self.classify(head), "blog-content")

    def test_a_blog_image_deploys_without_the_manual_step(self):
        head = self.repo.commit({"blog/static/images/a.webp": "img"}, "image")
        self.assertEqual(self.classify(head), "blog-content")

    def test_several_post_commits_since_the_deploy_still_count(self):
        self.repo.commit({"blog/content/one.md": "1"}, "one")
        head = self.repo.commit({"blog/content/two.md": "2"}, "two")
        self.assertEqual(self.classify(head), "blog-content")

    def test_a_blog_template_change_keeps_the_manual_step(self):
        head = self.repo.commit({"blog/templates/page.html": "<html>"}, "template")
        self.assertEqual(self.classify(head), "")

    def test_a_post_alongside_landing_copy_keeps_the_manual_step(self):
        self.repo.commit({"blog/content/a-post.md": "post"}, "post")
        head = self.repo.commit({"i18n/en.json": "{}"}, "copy")
        self.assertEqual(self.classify(head), "")

    def test_nothing_new_since_the_deploy_keeps_the_manual_step(self):
        self.assertEqual(self.classify(self.deployed), "")

    def test_a_deployed_commit_the_checkout_lacks_keeps_the_manual_step(self):
        head = self.repo.commit({"blog/content/a-post.md": "post"}, "post")
        self.assertEqual(self.classify(head, deployed="0" * 40), "")

    def test_an_unknown_deployed_commit_keeps_the_manual_step(self):
        head = self.repo.commit({"blog/content/a-post.md": "post"}, "post")
        self.assertEqual(self.classify(head, deployed=""), "")

    def test_an_unreadable_build_info_writes_an_empty_decision(self):
        head = self.repo.commit({"blog/content/a-post.md": "post"}, "post")
        dotenv = Path(self.tmp.name) / "deploy.env"

        classifier.main(
            [
                "--repo", str(self.repo.root),
                "--head", head,
                "--build-info-url", (Path(self.tmp.name) / "missing.json").as_uri(),
                "--dotenv", str(dotenv),
            ]
        )

        self.assertEqual(dotenv.read_text(), "DEPLOY_AUTO=\n")


if __name__ == "__main__":
    unittest.main()
