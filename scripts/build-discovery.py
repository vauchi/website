#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Export agent-readable versions of the already-published site content."""

import re
import sys
import tomllib
from html.parser import HTMLParser
from pathlib import Path


class ReadablePage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.body = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.body = True
        if not self.body:
            return
        if tag in ("h1", "h2", "h3"):
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("p", "li", "section"):
            self.parts.append("\n\n" + ("- " if tag == "li" else ""))

    def handle_data(self, data):
        if self.body and data.strip():
            self.parts.append(data.strip() + " ")

    def handle_endtag(self, tag):
        if tag == "main":
            self.body = False

    def markdown(self):
        return re.sub(r"[ \t]+\n", "\n", "".join(self.parts)).strip() + "\n"


def generate(root):
    public = root / "public"
    for source in [public / "text/index.html", *public.glob("*/text/index.html")]:
        if not source.is_file():
            continue
        parser = ReadablePage()
        parser.feed(source.read_text())
        source.parent.parent.joinpath("index.md").write_text(parser.markdown())
    blog = public / "blog"
    if not (blog / "index.html").is_file():
        raise ValueError("build the blog before generating discovery")
    config = tomllib.loads((root / "blog/config.toml").read_text())
    base = config["base_url"].rstrip("/")
    entries = []
    for source in sorted((root / "blog/content").glob("*.md")):
        if source.name.startswith("_"):
            continue
        pieces = source.read_text().split("+++", 2)
        metadata = tomllib.loads(pieces[1])
        slug = metadata.get("slug", source.stem)
        if "/" in slug or slug in (".", ".."):
            raise ValueError("invalid public blog slug")
        destination = blog / slug / "index.md"
        if not destination.with_name("index.html").is_file():
            raise ValueError(f"blog page not built: {slug}")
        title = metadata["title"]
        destination.write_text(f"# {title}\n\n" + pieces[2].lstrip())
        entries.append((title, f"{base}/{slug}/index.md"))
    index = f"# {config['title']}\n\n> {config['description']}\n\n## Articles\n\n"
    index += "".join(f"- [{title}]({url})\n" for title, url in entries)
    (blog / "index.md").write_text(index)
    (blog / "llms.txt").write_text(index)
    overview = public / "llms.txt"
    text = re.sub(r"(https://vauchi\.app/(?:docs|spec)/[^\s)]+)\.html", r"\1.md", overview.read_text())
    if "## Section overviews" not in text:
        text += "\n## Section overviews\n\n" + "".join(
            f"- [{name}](https://vauchi.app/{name.lower()}/llms.txt)\n"
            for name in ("Blog", "Docs", "Spec")
        )
    overview.write_text(text)
    print(f"Discovery: landing Markdown and {len(entries)} blog articles")


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd())
