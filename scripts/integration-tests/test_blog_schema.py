# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from test_blog_json import BLOG, JsonScripts

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_schema import Page, validate_tree


class Metadata(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.meta = {}
        self.text = []
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            self.meta[attrs.get("property", attrs.get("name"))] = attrs.get("content")

    def handle_data(self, data):
        self.text.append(data)


class BlogSchemaTests(unittest.TestCase):
    def test_real_blog_build_links_author_dates_and_inventory_to_visible_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "blog"
            shutil.copytree(BLOG, root)
            post = next(path for path in sorted((root / "content").glob("*.md")) if path.name != "_index.md")
            timestamp = "2026-11-01T10:20:30+00:00"
            (root / "source-dates.json").write_text(json.dumps({
                post.name: {"dateModified": timestamp, "sha256": "fixture"}
            }))
            output = root / "output"
            result = subprocess.run(
                [os.environ.get("ZOLA_BIN") or shutil.which("zola"), "--root", str(root),
                 "build", "--output-dir", str(output), "--base-url", "http://localhost:3000/blog"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            index = json.loads(JsonScripts((output / "index.html").read_text()).blocks[0][1])
            self.assertEqual(index["@type"], "Blog")
            articles = []
            for page in output.glob("*/index.html"):
                if page.parent.name == "admin":
                    continue
                document = page.read_text()
                blocks = JsonScripts(document).blocks
                self.assertEqual(len(blocks), 1)
                article = json.loads(blocks[0][1])
                visible = Metadata(document)
                self.assertEqual(article["@type"], "BlogPosting")
                self.assertEqual(article["description"], visible.meta["og:description"])
                self.assertEqual(article["image"], visible.meta["og:image"])
                self.assertEqual(article["mainEntityOfPage"], visible.meta["og:url"])
                self.assertEqual(article["author"], {"@id": "https://vauchi.app/#organization"})
                self.assertEqual(article["publisher"], article["author"])
                self.assertIn("By", " ".join(visible.text))
                self.assertIn("Vauchi", " ".join(visible.text))
                self.assertIn("Mattia Egloff", " ".join(visible.text))
                self.assertIn("AI-assisted.", " ".join(visible.text))
                self.assertNotIn("http://localhost", blocks[0][1])
                if "dateModified" in article:
                    self.assertEqual(article["dateModified"], timestamp)
                    self.assertNotIn(timestamp, Page(document).times)
                    self.assertEqual(article["dateModified"], visible.meta["article:modified_time"])
                articles.append(article)
            self.assertEqual(sum("dateModified" in article for article in articles), 1)
            self.assertEqual(
                sorted((post["name"], post["url"], post["datePublished"]) for post in index["blogPost"]),
                sorted((post["headline"], post["mainEntityOfPage"], post["datePublished"]) for post in articles),
            )
            self.assertEqual(validate_tree(output)[1], len(articles) + 1)
