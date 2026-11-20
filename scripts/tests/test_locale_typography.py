# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import re
import unittest

from scriptloader import REPO_ROOT

I18N = REPO_ROOT / "i18n"
NARROW_NO_BREAK_SPACE = " "
NO_BREAK_SPACE = " "


def strings(locale):
    def walk(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)

    data = json.loads((I18N / f"{locale}.json").read_text(encoding="utf-8"))
    return [(key, text) for key, value in data.items() for text in walk(value)]


class FrenchPunctuationSpacingTest(unittest.TestCase):
    # A plain space lets the browser break the line before the mark, so a
    # lone ":" or "?" can open the next line.
    def test_colons_follow_a_no_break_space(self):
        offenders = [key for key, text in strings("fr") if re.search(r"[  ]:", text)]
        self.assertEqual(offenders, [])

    def test_semicolons_and_question_and_exclamation_marks_follow_a_narrow_no_break_space(self):
        offenders = [key for key, text in strings("fr") if re.search(r"[  ][;?!]", text)]
        self.assertEqual(offenders, [])

    def test_the_rule_keeps_urls_and_placeholders_intact(self):
        for key, text in strings("fr"):
            with self.subTest(key=key):
                self.assertNotIn(f"https{NO_BREAK_SPACE}:", text)
                self.assertNotIn(f"http{NO_BREAK_SPACE}:", text)


class GermanInformalAddressTest(unittest.TestCase):
    # The site says "du"; a capitalised "Sie" is formal address unless it
    # opens a sentence, where it can be "they".
    def test_german_never_addresses_the_reader_formally(self):
        formal = re.compile(r"\b(Ihnen|Ihr|Ihre|Ihren|Ihrem|Ihrer|Ihres)\b|(?<![.!?:]\s)(?<!^)\bSie\b")
        offenders = [key for key, text in strings("de") if formal.search(text)]
        self.assertEqual(offenders, [])


class TypographicApostropheTest(unittest.TestCase):
    def test_french_and_italian_use_the_typographic_apostrophe(self):
        for locale in ("fr", "it"):
            with self.subTest(locale=locale):
                offenders = [key for key, text in strings(locale) if re.search(r"(?<=\w)'(?=\w)", text)]
                self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
