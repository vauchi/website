#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The CDN image is built only from a signed manifest.

Apps reject a manifest without a signature, so an image that ships one
stops every content update (vauchi/private#1244).
"""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

WEBSITE = Path(__file__).resolve().parents[2]
GUARD = WEBSITE / "cdn" / "require-signed-manifest.sh"
SIGNATURE = "ab" * 64


def run_guard(manifest_text):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "manifest.json"
        if manifest_text is not None:
            path.write_text(manifest_text, encoding="utf-8")
        return subprocess.run(
            ["sh", str(GUARD), str(path)], capture_output=True, text=True
        )


def manifest(**extra):
    return json.dumps({"schema_version": 1, "content": {}, **extra}, indent=2)


def cdn_image_needs():
    ci = (WEBSITE / ".gitlab-ci.yml").read_text(encoding="utf-8")
    job = re.search(r"^build:cdn-docker:\n((?:[ \n].*\n)*)", ci, re.M).group(1)
    needs = re.search(r"^  needs:\n((?:    .*\n)*)", job, re.M).group(1)
    return needs


class RequireSignedManifestTest(unittest.TestCase):
    def test_a_signed_manifest_passes(self):
        result = run_guard(manifest(signature=SIGNATURE))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_manifest_without_a_signature_is_refused(self):
        result = run_guard(manifest())
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsigned", result.stderr)

    def test_a_malformed_signature_is_refused(self):
        for signature in ["", "ab" * 63, "zz" * 64, None]:
            with self.subTest(signature=signature):
                result = run_guard(manifest(signature=signature))
                self.assertEqual(result.returncode, 1)

    def test_a_missing_manifest_is_refused(self):
        result = run_guard(None)
        self.assertEqual(result.returncode, 1)


class CdnImageInputsTest(unittest.TestCase):
    def test_the_image_takes_its_files_from_the_signing_job_alone(self):
        needs = cdn_image_needs()
        self.assertEqual(re.findall(r"job: (\S+)", needs), ["sign:content"])
        self.assertNotIn("optional", needs)

    def test_the_image_build_runs_the_guard_before_kaniko(self):
        ci = (WEBSITE / ".gitlab-ci.yml").read_text(encoding="utf-8")
        job = ci.split("build:cdn-docker:", 1)[1]
        guard = job.find("cdn/require-signed-manifest.sh public/app-files/manifest.json")
        self.assertGreater(guard, -1)
        self.assertLess(guard, job.find("/kaniko/executor"))


if __name__ == "__main__":
    unittest.main()
