#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for Ed25519 content manifest signing.

The signature covers the canonical JSON of the manifest without its
signature field, and clients verify it to decide whether downloaded
content is authentic. Real Ed25519 is used throughout — crypto is never
mocked (ADR-002).
"""

import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scriptloader import SCRIPTS_DIR, load

signer = load("sign-manifest.py")

from nacl.signing import SigningKey  # noqa: E402  (the script guards this import)

ACCENTED_MANIFEST = {
    "version": "1.0.0",
    "files": [{"path": "café.webp", "sha256": "ab" * 32}],
    "note": "Prénom — Español",
}


class Workspace:
    """A temp directory holding a manifest and a keypair."""

    def __init__(self, test_case, manifest: dict):
        tmp = tempfile.TemporaryDirectory()
        test_case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )

        signing_key = SigningKey.generate()
        self.private_path = self.root / "content-signing.key"
        self.public_path = self.root / "content-signing.pub"
        self.private_path.write_text(
            base64.b64encode(bytes(signing_key)).decode("ascii") + "\n"
        )
        self.public_path.write_text(
            base64.b64encode(bytes(signing_key.verify_key)).decode("ascii") + "\n"
        )

    def read(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def rewrite(self, manifest: dict) -> None:
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )


class CanonicalForm(unittest.TestCase):
    def test_keys_are_sorted_regardless_of_insertion_order(self):
        one = signer.canonical_json({"b": 1, "a": 2})
        other = signer.canonical_json({"a": 2, "b": 1})

        self.assertEqual(one, other)
        self.assertEqual(one, b'{"a":2,"b":1}')

    def test_nested_keys_are_sorted_too(self):
        self.assertEqual(
            signer.canonical_json({"outer": {"z": 1, "a": 2}}),
            b'{"outer":{"a":2,"z":1}}',
        )

    def test_separators_are_compact(self):
        self.assertNotIn(b" ", signer.canonical_json({"a": 1, "b": [1, 2]}))

    def test_non_ascii_is_encoded_as_utf8_not_escaped(self):
        canonical = signer.canonical_json({"name": "Café"})

        self.assertIn("Café".encode(), canonical)
        self.assertNotIn(b"\\u", canonical)

    def test_the_output_is_bytes_ready_to_sign(self):
        self.assertIsInstance(signer.canonical_json({}), bytes)

    def test_list_order_is_preserved(self):
        """Sorting applies to mapping keys, not to sequence elements."""
        self.assertEqual(signer.canonical_json({"a": [3, 1, 2]}), b'{"a":[3,1,2]}')


class SignAndVerify(unittest.TestCase):
    def test_a_signed_manifest_verifies(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)

        signer.sign_manifest(workspace.manifest_path, workspace.private_path)
        signer.verify_signature(workspace.manifest_path, workspace.public_path)

    def test_signing_embeds_a_hex_signature_of_the_expected_length(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)

        signer.sign_manifest(workspace.manifest_path, workspace.private_path)

        signature = workspace.read()["signature"]
        self.assertEqual(len(signature), 128, "Ed25519 signatures are 64 bytes")
        self.assertEqual(bytes.fromhex(signature).__len__(), 64)

    def test_signing_leaves_the_rest_of_the_manifest_untouched(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)

        signer.sign_manifest(workspace.manifest_path, workspace.private_path)

        signed = workspace.read()
        del signed["signature"]
        self.assertEqual(signed, ACCENTED_MANIFEST)

    def test_a_tampered_field_fails_verification(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)
        signer.sign_manifest(workspace.manifest_path, workspace.private_path)

        tampered = workspace.read()
        tampered["files"][0]["sha256"] = "cd" * 32
        workspace.rewrite(tampered)

        with self.assertRaises(SystemExit) as exit_code:
            signer.verify_signature(workspace.manifest_path, workspace.public_path)
        self.assertEqual(exit_code.exception.code, 1)

    def test_an_added_field_fails_verification(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)
        signer.sign_manifest(workspace.manifest_path, workspace.private_path)

        tampered = workspace.read()
        tampered["injected"] = "payload"
        workspace.rewrite(tampered)

        with self.assertRaises(SystemExit):
            signer.verify_signature(workspace.manifest_path, workspace.public_path)

    def test_a_removed_field_fails_verification(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)
        signer.sign_manifest(workspace.manifest_path, workspace.private_path)

        tampered = workspace.read()
        del tampered["note"]
        workspace.rewrite(tampered)

        with self.assertRaises(SystemExit):
            signer.verify_signature(workspace.manifest_path, workspace.public_path)

    def test_another_keys_signature_is_rejected(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)
        other = Workspace(self, ACCENTED_MANIFEST)
        signer.sign_manifest(workspace.manifest_path, workspace.private_path)

        with self.assertRaises(SystemExit):
            signer.verify_signature(workspace.manifest_path, other.public_path)

    def test_a_manifest_without_a_signature_is_rejected(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)

        with self.assertRaises(SystemExit) as exit_code:
            signer.verify_signature(workspace.manifest_path, workspace.public_path)
        self.assertEqual(exit_code.exception.code, 1)

    def test_an_empty_signature_is_rejected_rather_than_treated_as_absent(self):
        workspace = Workspace(self, {**ACCENTED_MANIFEST, "signature": ""})

        with self.assertRaises(SystemExit):
            signer.verify_signature(workspace.manifest_path, workspace.public_path)

    def test_reordering_keys_does_not_invalidate_the_signature(self):
        """Canonical form is what is signed, so byte layout must not matter."""
        workspace = Workspace(self, ACCENTED_MANIFEST)
        signer.sign_manifest(workspace.manifest_path, workspace.private_path)

        signed = workspace.read()
        workspace.rewrite(dict(reversed(list(signed.items()))))

        signer.verify_signature(workspace.manifest_path, workspace.public_path)

    def test_resigning_an_already_signed_manifest_is_stable(self):
        """The previous signature must be stripped before canonicalizing."""
        workspace = Workspace(self, ACCENTED_MANIFEST)

        signer.sign_manifest(workspace.manifest_path, workspace.private_path)
        first = workspace.read()["signature"]
        signer.sign_manifest(workspace.manifest_path, workspace.private_path)
        second = workspace.read()["signature"]

        self.assertEqual(first, second)
        signer.verify_signature(workspace.manifest_path, workspace.public_path)


class KeypairGeneration(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.key_dir = Path(tmp.name) / "keys"
        signer.generate_keypair(self.key_dir)
        self.private_path = self.key_dir / "content-signing.key"
        self.public_path = self.key_dir / "content-signing.pub"

    def test_both_key_files_are_written(self):
        self.assertTrue(self.private_path.is_file())
        self.assertTrue(self.public_path.is_file())

    def test_the_keys_are_base64_encoded_32_byte_values(self):
        for path in (self.private_path, self.public_path):
            with self.subTest(path=path.name):
                raw = base64.b64decode(path.read_text().strip())
                self.assertEqual(len(raw), 32)

    def test_the_private_key_is_not_world_readable(self):
        mode = self.private_path.stat().st_mode & 0o777

        self.assertEqual(mode, 0o600, f"private key mode is {oct(mode)}")

    def test_the_generated_pair_signs_and_verifies(self):
        workspace = Workspace(self, ACCENTED_MANIFEST)

        signer.sign_manifest(workspace.manifest_path, self.private_path)
        signer.verify_signature(workspace.manifest_path, self.public_path)

    def test_each_generated_pair_is_distinct(self):
        first = self.private_path.read_text()
        signer.generate_keypair(self.key_dir)

        self.assertNotEqual(first, self.private_path.read_text())


class NonUtf8Locale(unittest.TestCase):
    """CI containers commonly run with LC_ALL=C.

    The canonical form is explicitly UTF-8 and allows non-ASCII, so
    reading or writing the manifest in the locale's encoding would
    corrupt exactly the bytes the signature covers.
    """

    script = str(SCRIPTS_DIR / "sign-manifest.py")

    def _run(self, *args, env):
        return subprocess.run(
            [sys.executable, self.script, *args],
            capture_output=True,
            text=True,
            env=env,
        )

    def setUp(self):
        self.workspace = Workspace(self, ACCENTED_MANIFEST)
        self.env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("LANG", "LC_CTYPE", "PYTHONUTF8")
        }
        self.env["LC_ALL"] = "C"
        self.env["PYTHONUTF8"] = "0"
        self.env["PYTHONCOERCECLOCALE"] = "0"

    def test_an_accented_manifest_signs_under_a_posix_locale(self):
        result = self._run(
            "--manifest",
            str(self.workspace.manifest_path),
            "--private-key",
            str(self.workspace.private_path),
            env=self.env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_manifest_signed_under_a_posix_locale_verifies_under_utf8(self):
        signed = self._run(
            "--manifest",
            str(self.workspace.manifest_path),
            "--private-key",
            str(self.workspace.private_path),
            env=self.env,
        )
        self.assertEqual(signed.returncode, 0, signed.stderr)

        # Verification here runs in this process, under UTF-8.
        signer.verify_signature(
            self.workspace.manifest_path, self.workspace.public_path
        )

    def test_the_accented_content_survives_a_posix_locale_round_trip(self):
        self._run(
            "--manifest",
            str(self.workspace.manifest_path),
            "--private-key",
            str(self.workspace.private_path),
            env=self.env,
        )

        signed = self.workspace.read()
        self.assertEqual(signed["note"], ACCENTED_MANIFEST["note"])
        self.assertEqual(signed["files"][0]["path"], "café.webp")


if __name__ == "__main__":
    unittest.main()
