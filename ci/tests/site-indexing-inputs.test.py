# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The trigger must send literals before private validates its input schema."""

import re
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
            self.config[0]["spec"]["inputs"]["source_sha"]["default"],
            "$CI_COMMIT_SHA",
        )

    def test_internal_include_cannot_replace_sha_with_a_pipeline_input(self):
        includes = [
            item for item in self.root["include"] if item.get("local") == TEMPLATE
        ]
        self.assertEqual(includes, [{"local": TEMPLATE}])
        self.assertNotIn(
            "source_sha",
            documents(".gitlab-ci.yml")[0].get("spec", {}).get("inputs", {}),
        )

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


    def test_agent_bot_merge_requests_skip_the_trigger(self):
        # The bot cannot start pipelines on private's protected main
        # (vauchi/private#1284); the maintainer and main still run it.
        rules = self.job["rules"]
        mr = [i for i, r in enumerate(rules) if '"merge_request_event"' in r["if"]]
        skip, run = rules[mr[0]], rules[mr[1]]
        self.assertEqual(skip["when"], "never")
        self.assertNotIn("when", run)
        pattern = re.search(r"\$GITLAB_USER_LOGIN =~ /(.+)/'?$", skip["if"] + "'")
        self.assertIsNotNone(pattern, skip["if"])
        bot = re.compile(pattern.group(1))
        self.assertTrue(bot.search("group_122552022_bot_5269f4a65ce21963ed6123e3f9b78256"))
        self.assertTrue(bot.search("project_83_bot_0a1b2c"))
        self.assertFalse(bot.search("megloff1"))
        self.assertFalse(bot.search("someone_group_1_bot_x"))
        main = [r for r in rules if "CI_DEFAULT_BRANCH" in r["if"]]
        self.assertEqual(len(main), 1)
        self.assertNotIn("GITLAB_USER_LOGIN", main[0]["if"])

if __name__ == "__main__":
    unittest.main()

