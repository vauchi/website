# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Real renderer checks run by the CI job that installs pinned Zola."""

import json
import os
import random
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


BLOG = Path(__file__).resolve().parents[2] / "blog"
PROBE_TEMPLATE = '''{% extends "page.html" %}
{% block extra_head %}
{% set payloads = load_data(path="probes.json") %}
<script type="application/ld+json" id="probe-title">{{ <json value={page.title} /> }}</script>
<script type="application/ld+json" id="probe-payload">{{ <json value={payloads[page.slug]} /> }}</script>
{% endblock extra_head %}
'''


class JsonScripts(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.blocks = []
        self.active = False
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.active = dict(attrs).get("type") == "application/ld+json"
            if self.active:
                self.blocks.append([dict(attrs).get("id"), ""])

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.blocks[-1][1] += data


class BlogJsonTests(unittest.TestCase):
    def build(self, values, unsafe_control=False):
        binary = os.environ.get("ZOLA_BIN") or shutil.which("zola")
        self.assertIsNotNone(binary, "the pinned real Zola binary is required")
        version = subprocess.run([binary, "--version"], capture_output=True, text=True, check=True)
        self.assertEqual(version.stdout.strip(), "zola 0.23.6")
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        shutil.copytree(BLOG, root / "blog")
        root = root / "blog"
        (root / "templates/json-probe.html").write_text(PROBE_TEMPLATE)
        if unsafe_control:
            (root / "templates/components.html").write_text(
                '{% component json(value) %}{{ value | json_encode() | safe }}{% endcomponent json %}'
            )
        payloads = {}
        for index, value in enumerate(values):
            slug = f"json-probe-{index}"
            payloads[slug] = {"text": value, "nested": [value, {"unicode": "雪 café 👩‍💻"}], "number": index}
            (root / f"content/{slug}.md").write_text(
                '+++\ntitle = ' + json.dumps(value, ensure_ascii=False) + '\n'
                'description = "Serialization fixture."\ndate = 2026-01-01\n'
                f'slug = "{slug}"\ntemplate = "json-probe.html"\n+++\n'
                'A literal serialization control.\n'
            )
        (root / "probes.json").write_text(json.dumps(payloads, ensure_ascii=False))
        output = root / "output"
        result = subprocess.run(
            [binary, "--root", str(root), "build", "--output-dir", str(output),
             "--base-url", "http://localhost:3000/blog"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return output, payloads

    def test_values_round_trip_through_real_zola_and_delivered_html(self):
        fragments = ['"', "\\", "\n", "&", "<", ">", "雪", "\u2028", "\u2029",
                     "</script>", "<!-- vauchi-discovery:end -->"]
        rng = random.Random(1172)
        values = ["", "Plain title", "Literal \\u003c stays literal", "Quotes: \" & < > café 👩‍💻", "</script><p>literal</p>",
                  '</script><script type="application/ld+json">{"spoof":true}</script>',
                  "<!-- vauchi-discovery:start --><!-- vauchi-discovery:end -->"]
        values.extend("".join(rng.choices(fragments, k=8)) for _ in range(64))
        output, payloads = self.build(values)
        for index, value in enumerate(values):
            with self.subTest(index=index):
                slug = f"json-probe-{index}"
                document = (output / slug / "index.html").read_text()
                blocks = JsonScripts(document).blocks
                self.assertEqual([block[0] for block in blocks], ["probe-title", "probe-payload"])
                self.assertEqual(json.loads(blocks[0][1]), value)
                self.assertEqual(json.loads(blocks[1][1]), payloads[slug])
                self.assertNotIn("<", blocks[0][1])
                self.assertNotIn("<", blocks[1][1])

    def test_plain_json_encoding_is_rejected_by_the_same_html_boundary(self):
        output, _payloads = self.build(["A </script><p>literal</p> example"], unsafe_control=True)
        blocks = JsonScripts((output / "json-probe-0/index.html").read_text()).blocks
        with self.assertRaises(json.JSONDecodeError):
            json.loads(blocks[0][1])


if __name__ == "__main__":
    unittest.main()
