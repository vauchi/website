#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the waitlist service's input-handling helpers.

The waitlist holds subscriber email addresses, so the pieces that decide
where a visitor is sent, what counts as an address, and how a stored
address is protected are the ones worth pinning. Real AES-256-GCM
throughout; crypto is never mocked (ADR-002).

The module reads its configuration at import time and refuses to load
without an encryption key, so the environment is prepared before it is
imported.
"""

import base64
import importlib.util
import os
import sys
import unittest
from pathlib import Path

WAITLIST_DIR = Path(__file__).resolve().parent.parent

TEST_KEY = base64.b64encode(bytes(range(32))).decode("ascii")
REDIRECT_BASE = "https://vauchi.app/"


def _import_api():
    os.environ["WAITLIST_ENCRYPTION_KEY"] = TEST_KEY
    os.environ["WAITLIST_REDIRECT_BASE_URL"] = REDIRECT_BASE
    os.environ.setdefault("WAITLIST_DB_PATH", ":memory:")

    spec = importlib.util.spec_from_file_location(
        "vauchi_waitlist_api", WAITLIST_DIR / "api.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError("cannot load waitlist api.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["vauchi_waitlist_api"] = module
    spec.loader.exec_module(module)
    return module


api = _import_api()


class RedirectSafety(unittest.TestCase):
    """`_safe_redirect_url` is the open-redirect guard on a public endpoint."""

    def test_no_redirect_requested_returns_the_base(self):
        for empty in (None, ""):
            with self.subTest(value=empty):
                self.assertEqual(api._safe_redirect_url(empty), REDIRECT_BASE)

    def test_a_relative_path_is_joined_onto_the_base(self):
        self.assertEqual(
            api._safe_redirect_url("/thanks"), "https://vauchi.app/thanks"
        )

    def test_an_absolute_url_on_the_same_host_is_kept(self):
        self.assertEqual(
            api._safe_redirect_url("https://vauchi.app/thanks"),
            "https://vauchi.app/thanks",
        )

    def test_another_host_is_replaced_by_the_base(self):
        for hostile in (
            "https://evil.invalid/phish",
            "http://evil.invalid",
            "//evil.invalid/phish",
            "https://vauchi.app.evil.invalid/phish",
            "https://user:pw@evil.invalid/phish",
        ):
            with self.subTest(url=hostile):
                self.assertEqual(api._safe_redirect_url(hostile), REDIRECT_BASE)

    def test_a_query_string_or_fragment_is_not_carried_over(self):
        """Only the path is reused, so neither can smuggle anything through."""
        resolved = api._safe_redirect_url("/thanks?next=https://evil.invalid#x")

        self.assertEqual(resolved, "https://vauchi.app/thanks")

    def test_a_scheme_relative_authority_cannot_escape(self):
        self.assertEqual(api._safe_redirect_url("//evil.invalid"), REDIRECT_BASE)

    def test_a_non_http_scheme_on_no_host_still_resolves_under_the_base(self):
        resolved = api._safe_redirect_url("javascript:alert(1)")

        self.assertTrue(
            resolved.startswith(REDIRECT_BASE),
            f"resolved outside the base: {resolved}",
        )
        self.assertNotIn("javascript:", resolved)

    def test_every_result_stays_under_the_base(self):
        for candidate in (
            None,
            "",
            "/",
            "/thanks",
            "thanks",
            "https://vauchi.app/a/b",
            "https://evil.invalid/x",
            "//evil.invalid",
            "javascript:alert(1)",
            "../../etc/passwd",
        ):
            with self.subTest(url=candidate):
                self.assertTrue(
                    api._safe_redirect_url(candidate).startswith(REDIRECT_BASE),
                    f"{candidate!r} escaped the base",
                )


class EmailValidation(unittest.TestCase):
    def test_ordinary_addresses_are_accepted(self):
        for address in (
            "a@b.co",
            "first.last@example.com",
            "user+tag@example.co.uk",
            "user_name@example-host.com",
            "user%percent@example.com",
        ):
            with self.subTest(address=address):
                self.assertTrue(api._valid_email(address))

    def test_malformed_addresses_are_rejected(self):
        for address in (
            "",
            "no-at-sign",
            "@example.com",
            "user@",
            "user@host",
            "user@host.c",
            "user@@example.com",
            "user name@example.com",
            "user@exam ple.com",
            "user@example.com\nBcc: victim@example.com",
        ):
            with self.subTest(address=address):
                self.assertFalse(api._valid_email(address))

    def test_a_header_injection_attempt_is_rejected(self):
        """The address reaches an SMTP message, so newlines must not pass."""
        for payload in (
            "a@b.co\r\nBcc: victim@example.com",
            "a@b.co\nSubject: spam",
        ):
            with self.subTest(payload=payload):
                self.assertFalse(api._valid_email(payload))


class EmailHashing(unittest.TestCase):
    def test_the_hash_is_stable_for_the_same_address(self):
        self.assertEqual(api._hash_email("a@b.co"), api._hash_email("a@b.co"))

    def test_case_and_surrounding_whitespace_are_normalized_away(self):
        canonical = api._hash_email("user@example.com")

        for variant in ("USER@EXAMPLE.COM", "  user@example.com  ", "User@Example.Com"):
            with self.subTest(variant=variant):
                self.assertEqual(api._hash_email(variant), canonical)

    def test_different_addresses_hash_differently(self):
        self.assertNotEqual(
            api._hash_email("a@b.co"), api._hash_email("c@d.co")
        )

    def test_the_hash_does_not_contain_the_address(self):
        digest = api._hash_email("user@example.com")

        self.assertNotIn("user", digest)
        self.assertNotIn("example", digest)
        self.assertEqual(len(digest), 64)


class Encryption(unittest.TestCase):
    def test_a_value_round_trips(self):
        self.assertEqual(api._decrypt(api._encrypt("user@example.com")), "user@example.com")

    def test_non_ascii_round_trips(self):
        self.assertEqual(api._decrypt(api._encrypt("Prénom — café")), "Prénom — café")

    def test_the_ciphertext_does_not_contain_the_plaintext(self):
        token = api._encrypt("user@example.com")

        self.assertNotIn("user@example.com", token)
        self.assertNotIn("user@example.com", base64.b64decode(token).decode("latin-1"))

    def test_encrypting_the_same_value_twice_gives_different_ciphertexts(self):
        """A fresh nonce each time, so equal addresses are not linkable."""
        self.assertNotEqual(api._encrypt("a@b.co"), api._encrypt("a@b.co"))

    def test_a_tampered_ciphertext_is_rejected(self):
        raw = bytearray(base64.b64decode(api._encrypt("user@example.com")))
        raw[-1] ^= 0x01
        tampered = base64.b64encode(bytes(raw)).decode("ascii")

        with self.assertRaises(Exception):
            api._decrypt(tampered)

    def test_a_tampered_nonce_is_rejected(self):
        raw = bytearray(base64.b64decode(api._encrypt("user@example.com")))
        raw[0] ^= 0x01
        tampered = base64.b64encode(bytes(raw)).decode("ascii")

        with self.assertRaises(Exception):
            api._decrypt(tampered)

    def test_the_nonce_is_the_documented_length(self):
        raw = base64.b64decode(api._encrypt(""))

        self.assertEqual(api.AESGCM_NONCE_SIZE, 12)
        self.assertGreater(len(raw), api.AESGCM_NONCE_SIZE)


class EncryptionKeyLoading(unittest.TestCase):
    def _load_with(self, value):
        previous = os.environ.get("WAITLIST_ENCRYPTION_KEY")
        self.addCleanup(
            lambda: os.environ.__setitem__("WAITLIST_ENCRYPTION_KEY", previous or "")
        )
        if value is None:
            os.environ.pop("WAITLIST_ENCRYPTION_KEY", None)
        else:
            os.environ["WAITLIST_ENCRYPTION_KEY"] = value
        return api._load_encryption_key()

    def test_a_valid_key_decodes_to_32_bytes(self):
        self.assertEqual(len(self._load_with(TEST_KEY)), 32)

    def test_an_absent_key_is_refused(self):
        with self.assertRaises(RuntimeError) as raised:
            self._load_with(None)

        self.assertIn("required", str(raised.exception))

    def test_an_empty_key_is_refused(self):
        with self.assertRaises(RuntimeError):
            self._load_with("")

    def test_a_short_key_is_refused(self):
        with self.assertRaises(RuntimeError) as raised:
            self._load_with(base64.b64encode(b"too short").decode("ascii"))

        self.assertIn("32 bytes", str(raised.exception))

    def test_an_over_long_key_is_refused(self):
        with self.assertRaises(RuntimeError):
            self._load_with(base64.b64encode(bytes(64)).decode("ascii"))


if __name__ == "__main__":
    unittest.main()
