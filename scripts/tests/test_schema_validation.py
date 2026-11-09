# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schema_vocabulary import Vocabulary
from validate_schema import validate_document


ORGANIZATION = "https://vauchi.app/#organization"
ARTICLE = {
    "@context": "https://schema.org", "@type": "BlogPosting",
    "headline": "Visible title", "description": "Visible description.",
    "datePublished": "2026-01-02", "dateModified": "2026-02-03T10:20:30+00:00",
    "mainEntityOfPage": "https://vauchi.app/blog/post/",
    "image": "https://vauchi.app/social-preview.png",
    "author": {"@id": ORGANIZATION}, "publisher": {"@id": ORGANIZATION},
}


def document(entities):
    blocks = ''.join('<script type="application/ld+json">' + json.dumps(entity) + '</script>'
                     for entity in entities)
    return (
        '<html><head><link rel="canonical" href="https://vauchi.app/blog/post/">'
        '<meta property="og:description" content="Visible description.">'
        '<meta property="og:image" content="https://vauchi.app/social-preview.png">'
        '<meta property="article:modified_time" content="2026-02-03T10:20:30+00:00">'
        + blocks + '</head><body><h1>Visible title</h1>'
        '<a rel="author" href="https://vauchi.app/authors/vauchi/">Vauchi</a>'
        '<time datetime="2026-01-02">January 2, 2026</time>'
        '<time datetime="2026-02-03T10:20:30+00:00">February 3, 2026</time>'
        '</body></html>'
    )


class SchemaValidationTests(unittest.TestCase):
    def test_clean_article_passes_full_vocabulary_and_content_validation(self):
        self.assertEqual(validate_document(document([ARTICLE])), 1)

    def test_real_vocabulary_rejects_types_properties_domains_ranges_and_dates(self):
        vocabulary = Vocabulary()
        for replacement, diagnostic in [
            ({"@type": "FakeArticle"}, "unknown type"),
            ({"inventedProperty": "text"}, "unknown property"),
            ({"openingHours": "Monday"}, "not applicable"),
            ({"author": "Vauchi"}, "range"),
            ({"dateModified": "2026-02-30"}, "range"),
            ({"dateModified": "2026-02-03T10:20:30"}, "range"),
            ({"mainEntityOfPage": "/blog/post/"}, "absolute canonical URL"),
            ({"image": "[https://vauchi.app/image.png](https://vauchi.app/image.png)"}, "absolute canonical URL"),
            ({"description": ""}, "empty"),
            ({"description": None}, "empty"),
            ({"sameAs": []}, "empty"),
            ({"publisher": {"@id": "https://vauchi.app/#missing"}}, "unresolved"),
        ]:
            with self.subTest(replacement=replacement):
                entity = copy.deepcopy(ARTICLE)
                entity.update(replacement)
                with self.assertRaisesRegex(ValueError, diagnostic):
                    vocabulary.validate(entity)

    def test_missing_or_corrupt_vocabulary_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vocabulary.json"
            with self.assertRaises(OSError):
                Vocabulary(path)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, "vocabulary integrity"):
                Vocabulary(path)

    def test_duplicate_article_and_metadata_mismatches_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate article"):
            validate_document(document([ARTICLE, ARTICLE]))
        for field, value in [("headline", "Different title"), ("description", "Different summary"),
                             ("image", "https://vauchi.app/other.png"),
                             ("mainEntityOfPage", "https://vauchi.app/blog/other/")]:
            with self.subTest(field=field):
                entity = dict(ARTICLE, **{field: value})
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    validate_document(document([entity]))
        with self.assertRaisesRegex(ValueError, "visible author"):
            validate_document(document([ARTICLE]).replace('rel="author"', 'rel="other"'))

    def test_invalid_json_and_duplicate_keys_fail(self):
        for payload in ['{"@type":', '{"@type":"BlogPosting","@type":"TechArticle"}']:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate_document('<html><head><script type="application/ld+json">' + payload
                                      + '</script></head><body></body></html>')

    def test_non_json_numbers_are_rejected(self):
        entity = dict(ARTICLE, wordCount=float("nan"))
        with self.assertRaisesRegex(ValueError, "non-JSON number"):
            validate_document(document([entity]))
