# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The trigger must send literals before private validates its input schema."""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = "ci/site-indexing.yml"


def documents(path):
    return list(yaml.safe_load_all((ROOT / path).read_text()))


class IndexingInputContractTests(unittest.TestCase):
    def setUp(self):
        self.root = documents(".gitlab-ci.yml")[-1]
        self.config = (
            documents(TEMPLATE)
            if (ROOT / TEMPLATE).exists()
            else [self.root]
        )
        self.job = self.config[-1]["check:site-indexing"]

    def test_project_sent_to_validated_input_is_literal(self):
        self.assertEqual(
            self.job["trigger"]["inputs"]["indexing_project"], "vauchi/website"
        )

    def test_sha_is_expanded_in_upstream_configuration_before_validation(self):
        self.assertEqual(
            self.job["trigger"]["inputs"]["indexing_sha"],
            "$[[ inputs.source_sha | expand_vars ]]",
        )
        self.assertEqual(
            self.config[0]["spec"]["inputs"]["source_sha"],
            {"default": "$CI_COMMIT_SHA"},
        )

    def test_internal_include_cannot_replace_sha_with_a_pipeline_input(self):
        includes = [
            item for item in self.root["include"] if item.get("local") == TEMPLATE
        ]
        self.assertEqual(includes, [{"local": TEMPLATE}])
        self.assertNotIn("spec", documents(".gitlab-ci.yml")[0])

    def test_gate_mirrors_result_without_forwarding_variables(self):
        trigger = self.job["trigger"]
        self.assertEqual(trigger["project"], "vauchi/private")
        self.assertEqual(trigger["branch"], "main")
        self.assertEqual(trigger["strategy"], "mirror")
        self.assertEqual(trigger["inputs"]["site_indexing"], "local")
        self.assertEqual(
            trigger["forward"],
            {"yaml_variables": False, "pipeline_variables": False},
        )
        self.assertEqual(self.job["inherit"], {"variables": False})


if __name__ == "__main__":
    unittest.main()

