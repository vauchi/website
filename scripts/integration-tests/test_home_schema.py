# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_blog_json import JsonScripts


ROOT = Path(__file__).resolve().parents[2]


class HomeSchemaTests(unittest.TestCase):
    def test_homepage_graph_resolves_vauchi_author_and_preserves_three_types(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("scripts", "templates", "i18n", "public"):
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("blog", "app-files"))
            result = subprocess.run([sys.executable, str(root / "scripts/build-pages.py")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for language in ("", "de", "fr", "it", "es"):
                document = (root / "public" / language / "index.html").read_text()
                blocks = [json.loads(block[1]) for block in JsonScripts(document).blocks]
                self.assertEqual([block["@type"] for block in blocks],
                                 ["Organization", "WebSite", "SoftwareApplication"])
                self.assertEqual(blocks[0]["@id"], "https://vauchi.app/#organization")
                self.assertIn('property="og:image:alt"', document)
            profile = (root / "public/authors/vauchi/index.html").read_text()
            entity = json.loads(JsonScripts(profile).blocks[0][1])
            self.assertEqual(entity["@type"], "Organization")
            self.assertEqual(entity["@id"], "https://vauchi.app/#organization")
            self.assertEqual(entity["name"], "Vauchi")
            self.assertIn("Mattia Egloff", profile)
