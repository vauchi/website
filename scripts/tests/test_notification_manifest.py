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


HOMES = ["https://vauchi.app/" + suffix for suffix in ("", "de/", "es/", "fr/", "it/")]


def minimal_site(root, sitemap_urls):
    public = root / "public"
    (root / "blog/content").mkdir(parents=True)
    (root / "blog/config.toml").write_text('base_url="https://vauchi.app/blog"\ntitle="Blog"\ndescription="Articles"\n')
    (public / "blog").mkdir(parents=True)
    (public / "llms.txt").write_text("# Vauchi\n")
    for url in sitemap_urls + ["https://vauchi.app/blog/"]:
        page = public / url.removeprefix("https://vauchi.app/") / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("<head><title>Public</title></head><main>Text</main>")
    (public / "sitemap-pages.xml").write_text(
        "<urlset>" + "".join("<url><loc>" + url + "</loc></url>" for url in sitemap_urls) + "</urlset>")
    return public


def discover(root):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        env={key: value for key, value in os.environ.items() if key != "CI_COMMIT_SHA"},
        capture_output=True, text=True,
    )


class WhyPagesInventoryTests(unittest.TestCase):
    def test_why_pages_in_the_sitemap_are_fingerprinted_with_the_homes(self):
        why = ["https://vauchi.app/why/", "https://vauchi.app/de/why/no-directory/"]
        with tempfile.TemporaryDirectory() as directory:
            public = minimal_site(Path(directory), HOMES + why)
            result = discover(Path(directory))
            self.assertEqual(result.returncode, 0, result.stderr)
            pages = json.loads((public / "indexnow-manifest.json").read_text())["pages"]
            self.assertEqual(set(pages), set(HOMES + why + ["https://vauchi.app/blog/"]))

    def test_support_and_publisher_pages_in_the_sitemap_are_fingerprinted(self):
        listed = ["https://vauchi.app/support/", "https://vauchi.app/fr/support/", "https://vauchi.app/authors/vauchi/"]
        with tempfile.TemporaryDirectory() as directory:
            public = minimal_site(Path(directory), HOMES + listed)
            result = discover(Path(directory))
            self.assertEqual(result.returncode, 0, result.stderr)
            pages = json.loads((public / "indexnow-manifest.json").read_text())["pages"]
            self.assertEqual(set(pages), set(HOMES + listed + ["https://vauchi.app/blog/"]))

    def test_any_other_sitemap_url_is_still_refused(self):
        for stray in (
            "https://vauchi.app/text/", "https://vauchi.app/why/../x/", "https://evil.example/why/",
            "https://vauchi.app/support/../x/", "https://vauchi.app/xx/support/", "https://vauchi.app/authors/other/",
        ):
            with self.subTest(stray=stray), tempfile.TemporaryDirectory() as directory:
                minimal_site(Path(directory), HOMES + [stray])
                result = discover(Path(directory))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unexpected sitemap URL", result.stderr)

    def test_a_missing_home_page_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            minimal_site(Path(directory), HOMES[:4] + ["https://vauchi.app/why/"])
            result = discover(Path(directory))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("incomplete landing inventory", result.stderr)


if __name__ == "__main__":
    unittest.main()
