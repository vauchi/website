# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "build-discovery.py"
SHA = "a" * 40


class NotificationManifestTests(unittest.TestCase):
    def test_manifest_uses_canonical_pages_and_build_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public = root / "public"
            (public / "blog/article").mkdir(parents=True)
            (root / "blog/content").mkdir(parents=True)
            (root / "blog/config.toml").write_text(
                'base_url="https://vauchi.app/blog"\ntitle="Blog"\ndescription="Articles"\n')
            (root / "blog/content/article.md").write_text(
                '+++\ntitle="Article"\n+++\nPublic article.\n')
            (public / "llms.txt").write_text("# Vauchi\n")
            urls = ["https://vauchi.app/" + suffix for suffix in ("", "de/", "es/", "fr/", "it/")]
            for url in urls + ["https://vauchi.app/blog/", "https://vauchi.app/blog/article/"]:
                page = public / url.removeprefix("https://vauchi.app/") / "index.html"
                page.parent.mkdir(parents=True, exist_ok=True)
                page.write_text("<head><title>Public</title></head><main>Text</main>")
            (public / "sitemap-pages.xml").write_text(
                "<urlset>" + "".join("<url><loc>" + url + "</loc></url>" for url in urls) + "</urlset>")
            (public / "build-info.json").write_text(json.dumps({"sha": SHA, "built": "first"}))
            (public / "admin").mkdir()
            (public / "admin/index.html").write_text("Private admin shell")

            def generate():
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), str(root)],
                    env={key: value for key, value in os.environ.items() if key != "CI_COMMIT_SHA"},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads((public / "indexnow-manifest.json").read_text())

            first = generate()
            self.assertEqual(first["source_sha"], SHA)
            self.assertEqual(first["page_count"], 7)
            self.assertEqual(set(first["pages"]), set(urls + [
                "https://vauchi.app/blog/", "https://vauchi.app/blog/article/"]))
            article = public / "blog/article/index.html"
            self.assertEqual(first["pages"]["https://vauchi.app/blog/article/"],
                             hashlib.sha256(article.read_bytes()).hexdigest())
            (public / "build-info.json").write_text(json.dumps({"sha": SHA, "built": "later"}))
            self.assertEqual(generate(), first)
            article.write_text(article.read_text().replace("<title>Public", "<title>Edited"))
            self.assertNotEqual(generate()["pages"]["https://vauchi.app/blog/article/"],
                                first["pages"]["https://vauchi.app/blog/article/"])
            article.unlink()
            result = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("page not built", result.stderr)


if __name__ == "__main__":
    unittest.main()
