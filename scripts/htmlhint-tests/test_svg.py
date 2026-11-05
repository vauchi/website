# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SvgPairTests(unittest.TestCase):
    def check(self, svg):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "fixture.html"
            page.write_text('<!doctype html><html><head><title>SVG</title></head><body>' + svg + '</body></html>')
            command = ["htmlhint"] if shutil.which("htmlhint") else ["npx", "--yes", "htmlhint"]
            return subprocess.run(command + ["--config", str(ROOT / ".htmlhintrc"), "--rulesdir", str(ROOT / "scripts/htmlhint-svg-tag-pair.js"), str(page)], capture_output=True, text=True)

    def test_unclosed_svg_path_is_rejected(self):
        result = self.check('<svg><path d="M0 0"></svg>')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('svg-tag-pair', result.stdout)

    def test_both_valid_svg_path_forms_are_accepted(self):
        for path in ['<path d="M0 0"/>', '<path d="M0 0"></path>']:
            with self.subTest(path=path):
                result = self.check('<svg>' + path + '</svg>')
                self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
