# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import subprocess
import sys
from pathlib import Path

from test_source_dates import GitFixture


SCRIPT = Path(__file__).resolve().parents[1] / "prepare_blog.py"


class BlogDatesTests(GitFixture):
    def test_manifest_binds_dates_to_source_bytes_before_container_build(self):
        (self.root / "blog/content").mkdir(parents=True)
        self.commit("blog/content/post.md", "Article", "2026-01-02T10:00:00+00:00")
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = self.root / "blog/source-dates.json"
        data = json.loads(manifest.read_text())
        self.assertEqual(data["post.md"]["dateModified"], "2026-01-02T10:00:00+00:00")
        good = subprocess.run([sys.executable, str(SCRIPT), str(self.root), "--check"],
                              capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        (self.root / "blog/content/post.md").write_text("Changed after preparation")
        stale = subprocess.run([sys.executable, str(SCRIPT), str(self.root), "--check"],
                               capture_output=True, text=True)
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("source changed", stale.stderr)
