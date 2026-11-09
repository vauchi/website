# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scriptloader import load

dates = load("source_dates.py")


class GitFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repository"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.test")
        self.git("config", "user.name", "Fixture")

    def git(self, *args, **kwargs):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True, **kwargs).stdout.strip()

    def commit(self, name, text, timestamp):
        (self.root / name).write_text(text)
        self.git("add", "--", name)
        environment = dict(os.environ, GIT_AUTHOR_DATE=timestamp, GIT_COMMITTER_DATE=timestamp)
        self.git("commit", "-qm", "Fixture change", env=environment)


class SourceDatesTests(GitFixture):
    def test_source_date_survives_unrelated_commits_and_renames(self):
        self.commit("article.md", "Original", "2026-01-02T10:00:00+00:00")
        self.commit("template.html", "Unrelated", "2026-02-03T10:00:00+00:00")
        self.assertEqual(dates.last_modified(self.root, self.root / "article.md"),
                         "2026-01-02T10:00:00+00:00")
        self.git("mv", "article.md", "renamed.md")
        environment = dict(os.environ, GIT_AUTHOR_DATE="2026-03-04T10:00:00+00:00",
                           GIT_COMMITTER_DATE="2026-03-04T10:00:00+00:00")
        self.git("commit", "-qm", "Rename", env=environment)
        self.assertEqual(dates.last_modified(self.root, self.root / "renamed.md"),
                         "2026-03-04T10:00:00+00:00")

    def test_missing_history_untracked_and_modified_sources_omit_date(self):
        self.commit("article.md", "Original", "2026-01-02T10:00:00+00:00")
        (self.root / "article.md").write_text("Uncommitted")
        (self.root / "new.md").write_text("Untracked")
        self.assertIsNone(dates.last_modified(self.root, self.root / "article.md"))
        self.assertIsNone(dates.last_modified(self.root, self.root / "new.md"))
        outside = self.root.parent / "outside.md"
        outside.write_text("No repository")
        self.assertIsNone(dates.last_modified(self.root.parent, outside))

    def test_shallow_boundary_is_not_a_content_change(self):
        self.commit("article.md", "Original", "2026-01-02T10:00:00+00:00")
        self.commit("template.html", "Unrelated", "2026-02-03T10:00:00+00:00")
        clone = self.root.parent / "clone"
        subprocess.run(["git", "clone", "-q", "--depth=1", self.root.as_uri(), str(clone)], check=True)
        self.assertIsNone(dates.last_modified(clone, clone / "article.md"))
        subprocess.run(["git", "-C", str(clone), "fetch", "-q", "--unshallow"], check=True)
        self.assertEqual(dates.last_modified(clone, clone / "article.md"),
                         "2026-01-02T10:00:00+00:00")
