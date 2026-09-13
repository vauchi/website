#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for content schema validation.

This is the gate that stops malformed networks.json or locale files
reaching the manifest, so it is asserted to reject as well as accept.
"""

import json
import tempfile
import unittest
from pathlib import Path

from scriptloader import load

validator = load("validate-content.py")

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["name", "networks"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "networks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            },
        },
    },
    "additionalProperties": False,
}

VALID = {"name": "Vauchi", "networks": [{"id": "matrix"}]}


class Files:
    def __init__(self, test_case):
        tmp = tempfile.TemporaryDirectory()
        test_case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write(self, name: str, payload) -> Path:
        path = self.root / name
        text = payload if isinstance(payload, str) else json.dumps(payload)
        path.write_text(text, encoding="utf-8")
        return path


class LoadingJson(unittest.TestCase):
    def test_a_json_document_is_parsed(self):
        files = Files(self)

        self.assertEqual(validator.load_json(files.write("a.json", VALID)), VALID)

    def test_non_ascii_content_survives_the_read(self):
        files = Files(self)
        payload = {"name": "Café — Prénom", "networks": []}

        self.assertEqual(
            validator.load_json(files.write("a.json", payload))["name"],
            "Café — Prénom",
        )

    def test_malformed_json_raises_rather_than_returning_a_default(self):
        files = Files(self)

        with self.assertRaises(json.JSONDecodeError):
            validator.load_json(files.write("a.json", "{not json"))


class Validation(unittest.TestCase):
    def setUp(self):
        self.files = Files(self)
        self.schema_path = self.files.write("schema.json", SCHEMA)

    def check(self, payload) -> list[str]:
        return validator.validate_file(
            self.files.write("content.json", payload), self.schema_path
        )

    def test_a_conforming_document_reports_no_errors(self):
        self.assertEqual(self.check(VALID), [])

    def test_a_missing_required_field_is_reported(self):
        errors = self.check({"networks": []})

        self.assertEqual(len(errors), 1)
        self.assertIn("name", errors[0])

    def test_a_wrong_type_is_reported_against_its_field_path(self):
        errors = self.check({"name": 42, "networks": []})

        self.assertEqual(len(errors), 1)
        self.assertIn("name:", errors[0])

    def test_a_violation_inside_an_array_names_its_index(self):
        errors = self.check({"name": "V", "networks": [{"id": "ok"}, {}]})

        self.assertEqual(len(errors), 1)
        self.assertIn("networks.1", errors[0])

    def test_a_root_level_violation_is_labelled_root(self):
        errors = self.check({"name": "V", "networks": [], "extra": True})

        self.assertEqual(len(errors), 1)
        self.assertIn("(root)", errors[0])

    def test_every_violation_is_reported_not_just_the_first(self):
        errors = self.check({"name": 42, "networks": "not-an-array"})

        self.assertEqual(len(errors), 2)

    def test_malformed_content_is_reported_rather_than_raised(self):
        errors = validator.validate_file(
            self.files.write("content.json", "{not json"), self.schema_path
        )

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("Invalid JSON: "))

    def test_a_malformed_schema_is_reported_distinctly_from_bad_content(self):
        errors = validator.validate_file(
            self.files.write("content.json", VALID),
            self.files.write("broken.schema.json", "{not json"),
        )

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("Invalid schema JSON: "))

    def test_an_empty_document_against_a_permissive_schema_passes(self):
        errors = validator.validate_file(
            self.files.write("content.json", {}),
            self.files.write("any.schema.json", {}),
        )

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
