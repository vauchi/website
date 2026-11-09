#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fail builds on invalid emitted vocabulary or contradictory page facts."""

import json
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from schema_vocabulary import ORGANIZATION, Vocabulary


class Page(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.blocks, self.meta, self.headings, self.authors, self.times = [], {}, [], [], []
        self.in_head = self.in_script = self.in_heading = self.in_author = False
        self.canonical = None
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head":
            self.in_head = True
        if tag == "script":
            self.in_script = attrs.get("type") == "application/ld+json"
            if self.in_script:
                if not self.in_head:
                    raise ValueError("schema outside HTML head")
                self.blocks.append("")
        if self.in_head and tag == "meta":
            key = attrs.get("property", attrs.get("name"))
            self.meta[key] = attrs.get("content")
        if self.in_head and tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
        if tag == "h1":
            self.in_heading = True
            self.headings.append("")
        if tag == "a" and "author" in attrs.get("rel", "").split():
            self.in_author = True
            self.authors.append("")
        if tag == "time":
            self.times.append(attrs.get("datetime"))

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        if tag == "script":
            self.in_script = False
        if tag == "h1":
            self.in_heading = False
        if tag == "a":
            self.in_author = False

    def handle_data(self, data):
        if self.in_script:
            self.blocks[-1] += data
        if self.in_heading:
            self.headings[-1] += data
        if self.in_author:
            self.authors[-1] += data


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"non-JSON number: {value}")


def validate_document(document, vocabulary=None):
    vocabulary = vocabulary or Vocabulary()
    page = Page(document)
    entities = [json.loads(block, object_pairs_hook=unique_object, parse_constant=reject_constant)
                for block in page.blocks]
    kinds = Counter(entity.get("@type") for entity in entities)
    if kinds["BlogPosting"] + kinds["TechArticle"] > 1:
        raise ValueError("duplicate article blocks")
    for entity in entities:
        vocabulary.validate(entity)
        kind = entity.get("@type")
        if kind not in {"BlogPosting", "TechArticle", "AboutPage", "WebPage"}:
            continue
        for field in ("headline", "description", "author", "publisher", "mainEntityOfPage"):
            if field not in entity:
                raise ValueError(f"missing article property: {field}")
        heading = " ".join(page.headings[0].split()) if page.headings else None
        expected = {"headline": heading, "description": page.meta.get("og:description"),
                    "mainEntityOfPage": page.canonical}
        if kind == "BlogPosting":
            expected["image"] = page.meta.get("og:image")
            if "datePublished" not in entity or entity["datePublished"] not in page.times:
                raise ValueError("visible publication date mismatch")
            if "dateModified" in entity and entity["dateModified"] != page.meta.get("article:modified_time"):
                raise ValueError("Open Graph modification date mismatch")
        for field, value in expected.items():
            if value is None or entity.get(field) != value:
                raise ValueError(f"visible/metadata mismatch: {field}")
        if "Vauchi" not in [" ".join(author.split()) for author in page.authors]:
            raise ValueError("missing visible author attribution")
        for field in ("author", "publisher"):
            if entity[field] != {"@id": ORGANIZATION}:
                raise ValueError(f"unexpected {field} identity")
    canonical = page.canonical or ""
    if canonical.startswith("https://vauchi.app/blog/") and page.headings:
        required = "Blog" if canonical == "https://vauchi.app/blog/" else "BlogPosting"
        if kinds[required] != 1:
            raise ValueError(f"missing required schema: {required}")
    if canonical.startswith(("https://vauchi.app/docs/", "https://vauchi.app/spec/")) and not entities:
        raise ValueError("missing book page schema")
    return len(entities)


def validate_tree(root):
    vocabulary = Vocabulary()
    pages = blocks = 0
    for path in sorted(root.rglob("*.html")):
        try:
            blocks += validate_document(path.read_text(encoding="utf-8"), vocabulary)
        except (ValueError, TypeError) as error:
            raise ValueError(f"{path.relative_to(root)}: {error}") from error
        pages += 1
    if not pages or not blocks:
        raise ValueError("no pages or JSON-LD found; validation incomplete")
    print(f"Schema.org 30.1 offline validation: {pages} HTML pages, {blocks} blocks; 0 errors")
    return pages, blocks


if __name__ == "__main__":
    validate_tree(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("public"))
