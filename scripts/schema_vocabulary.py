# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Validate this site's plain JSON-LD against pinned Schema.org terms.

This is an offline vocabulary/domain/range check, not Google's eligibility
test or a general JSON-LD processor. Unsupported shapes fail closed.
"""

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit


ORGANIZATION = "https://vauchi.app/#organization"
VOCABULARY_SHA256 = "958b3995c0c992550f28606af4267447c51b22387bfb712d9e99536c145d1da0"
URL_PROPERTIES = {"url", "image", "logo", "mainEntityOfPage", "sameAs"}


def absolute_url(value):
    if not isinstance(value, str) or re.search(r'[\s<>\[\]()]', value):
        raise ValueError("expected an absolute canonical URL")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("expected an absolute canonical URL")


class Vocabulary:
    def __init__(self, path=None):
        payload = (path or Path(__file__).with_name("schemaorg-30.1.json")).read_bytes()
        if hashlib.sha256(payload).hexdigest() != VOCABULARY_SHA256:
            raise ValueError("vocabulary integrity failure")
        self.terms = json.loads(payload)["terms"]

    def ancestors(self, kind):
        if kind not in self.terms or self.terms[kind]["kind"] != "class":
            raise ValueError(f"unknown type: {kind}")
        result, pending = set(), [kind]
        while pending:
            name = pending.pop()
            if name not in result:
                result.add(name)
                pending.extend(self.terms.get(name, {}).get("parents", []))
        return result

    def validate(self, entity):
        identities = {ORGANIZATION: "Organization"}

        def collect(node):
            if isinstance(node, dict):
                if "@id" in node and "@type" in node:
                    identities[node["@id"]] = node["@type"]
                for child in node.values():
                    collect(child)
            elif isinstance(node, list):
                for child in node:
                    collect(child)

        collect(entity)
        self.check_node(entity, identities)

    def check_node(self, node, identities):
        if not isinstance(node, dict) or not node:
            raise ValueError("expected nonempty JSON-LD object")
        if "@context" in node and node["@context"] not in ("https://schema.org", "https://schema.org/"):
            raise ValueError("unsupported JSON-LD context")
        if "@id" in node:
            absolute_url(node["@id"])
        kind = node.get("@type") or identities.get(node.get("@id"))
        if kind is None:
            raise ValueError("unresolved identifier or missing type")
        parents = self.ancestors(kind)
        for key, value in node.items():
            if value is None or value == "" or value == [] or value == {}:
                raise ValueError(f"empty property: {key}")
            if key in {"@context", "@type", "@id"}:
                continue
            if key not in self.terms or self.terms[key]["kind"] != "property":
                raise ValueError(f"unknown property: {key}")
            term = self.terms[key]
            if not parents.intersection(term["domains"]):
                raise ValueError(f"property not applicable: {kind}.{key}")
            for child in value if isinstance(value, list) else [value]:
                if key in URL_PROPERTIES and isinstance(child, str):
                    absolute_url(child)
                if isinstance(child, dict):
                    self.check_node(child, identities)
                    child_kind = child.get("@type") or identities.get(child.get("@id"))
                    valid = bool(self.ancestors(child_kind).intersection(term["ranges"]))
                else:
                    valid = any(self.literal(child, allowed) for allowed in term["ranges"])
                if not valid:
                    raise ValueError(f"invalid range: {key}")

    def literal(self, value, allowed):
        try:
            if allowed == "Boolean":
                return isinstance(value, bool)
            if allowed in {"Number", "Integer", "Float"}:
                return not isinstance(value, bool) and isinstance(value, (int, float))
            if not isinstance(value, str):
                return False
            if allowed == "Text":
                return bool(value)
            if allowed == "URL":
                absolute_url(value)
                return True
            if allowed == "Date":
                return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)) and bool(date.fromisoformat(value))
            if allowed == "DateTime":
                return "T" in value and datetime.fromisoformat(value).utcoffset() is not None
        except ValueError:
            return False
        return False
