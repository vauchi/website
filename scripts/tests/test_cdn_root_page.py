#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""cdn.vauchi.app explains itself at its root and nowhere else.

A visitor who opens the bare host gets a page saying what the CDN is;
every other unknown path still answers 404 (vauchi/private#1244).
"""

import re
import unittest
from pathlib import Path

CDN = Path(__file__).resolve().parents[2] / "cdn"


def location(conf, matcher):
    match = re.search(r"location " + re.escape(matcher) + r" \{\n(.*?)\n    \}", conf, re.S)
    return match.group(1) if match else None


class CdnRootPageTest(unittest.TestCase):
    def setUp(self):
        self.conf = (CDN / "nginx-cdn.conf").read_text(encoding="utf-8")
        self.page = (CDN / "index.html").read_text(encoding="utf-8")

    def test_the_root_serves_the_page(self):
        root = location(self.conf, "= /")
        self.assertIsNotNone(root)
        self.assertIn("try_files /index.html =404;", root)

    def test_the_root_page_loads_nothing_from_anywhere(self):
        root = location(self.conf, "= /")
        self.assertIn("Content-Security-Policy \"default-src 'none'; style-src 'unsafe-inline'", root)
        self.assertNotRegex(self.page, r"<script|<link|<img|src=")

    def test_the_root_page_keeps_the_server_security_headers(self):
        root = location(self.conf, "= /")
        for header in ["X-Content-Type-Options", "X-Frame-Options", "Permissions-Policy"]:
            with self.subTest(header=header):
                self.assertIn(header, root)

    def test_other_unknown_paths_still_answer_404(self):
        self.assertIn("return 404;", location(self.conf, "/"))

    def test_the_page_points_to_the_privacy_policy(self):
        self.assertIn("https://vauchi.app/docs/legal/privacy-policy.html", self.page)

    def test_the_image_ships_the_page(self):
        dockerfile = (CDN / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY cdn/index.html /usr/share/nginx/html/index.html", dockerfile)


if __name__ == "__main__":
    unittest.main()
