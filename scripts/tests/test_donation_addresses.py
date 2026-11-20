#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Donation addresses in funding.json, their validators and QR codes (vauchi/private#1307)."""

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from scriptloader import REPO_ROOT, load

donations = load("donation_addresses.py")

FUNDING_JSON = REPO_ROOT / "public" / "funding.json"
WELL_KNOWN_FUNDING_JSON = REPO_ROOT / "public" / ".well-known" / "funding.json"
SIGNED_LIST = REPO_ROOT / "public" / "donation-addresses.txt.asc"
PUBLISHED_KEY = REPO_ROOT / "public" / ".well-known" / "pgp-key.txt"
# The key security.txt names: the signature must come from it.
SIGNING_KEY_FINGERPRINT = "4347B1C657A397E5206E4709A84E1AABD7830274"

# Pinned on purpose: changing an address must touch this test too, so a
# swapped address cannot reach the site in a one-line diff.
OWNER_ADDRESSES = {
    "bitcoin-silent-payments": "sp1qqtpujd9vfhx4jzh4xtjndmfazssfq64hrqx5082re0kdmzh5sj466q5n29n83gqst884p3yn8ek9k6r6qf92cm7wmnd9nddml0lvxxm5rcprygzt",
    "bitcoin": "bc1pykga6j933ss43xmad2layn3ln99e29r9s2t8rwmmrn5f98p2x92sz42fep",
    "monero": "83bHi5sfzVCDGyGmjEnGKgX31JruNzjF3crafNMwWowZeEE2rWYLsK3fdwYZP5HXkn8ynwu5wVK82Um8kataXUf62a8f7kg",
}


def single_character_typos(address: str, alphabet: str):
    for position, original in enumerate(address):
        replacement = next(c for c in alphabet if c != original)
        yield position, address[:position] + replacement + address[position + 1 :]


class PublishedAddressesTest(unittest.TestCase):
    def test_funding_json_publishes_the_owner_addresses(self):
        self.assertEqual(donations.load_donation_addresses(FUNDING_JSON), OWNER_ADDRESSES)

    def test_well_known_funding_json_is_the_same_document(self):
        self.assertEqual(
            WELL_KNOWN_FUNDING_JSON.read_bytes(),
            FUNDING_JSON.read_bytes(),
        )

    def test_every_plan_names_only_declared_channels(self):
        funding = json.loads(FUNDING_JSON.read_text(encoding="utf-8"))["funding"]
        declared = {channel["guid"] for channel in funding["channels"]}
        for plan in funding["plans"]:
            self.assertEqual(set(plan["channels"]) - declared, set(), plan["guid"])

    def test_any_amount_plan_accepts_every_donation_address(self):
        funding = json.loads(FUNDING_JSON.read_text(encoding="utf-8"))["funding"]
        any_amount = next(plan for plan in funding["plans"] if plan["guid"] == "any-amount")
        self.assertLessEqual(set(OWNER_ADDRESSES), set(any_amount["channels"]))


class QrCodeTest(unittest.TestCase):
    def test_each_committed_qr_code_is_rendered_from_its_published_address(self):
        for guid, address in OWNER_ADDRESSES.items():
            with self.subTest(guid=guid):
                committed = donations.qr_svg_path(guid).read_text(encoding="utf-8")
                self.assertEqual(committed, donations.render_qr_svg(address))

    def test_a_qr_code_for_another_address_differs(self):
        committed = donations.qr_svg_path("monero").read_text(encoding="utf-8")
        self.assertNotEqual(committed, donations.render_qr_svg(OWNER_ADDRESSES["bitcoin"]))


class SignedListTest(unittest.TestCase):
    """The out-of-band anchor: a change to funding.json alone cannot pass."""

    def verify(self, signed_bytes):
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, "GNUPGHOME": home}
            subprocess.run(["gpg", "--batch", "--quiet", "--import", str(PUBLISHED_KEY)],
                           env=env, check=True, capture_output=True)
            status = subprocess.run(["gpg", "--batch", "--status-fd", "1", "--decrypt"],
                                    input=signed_bytes, env=env, capture_output=True)
            return status.stdout.decode("utf-8", "replace")

    def test_the_list_is_signed_by_the_published_key(self):
        status = self.verify(SIGNED_LIST.read_bytes())
        validsig = re.search(r"^\[GNUPG:\] VALIDSIG (\S+(?: \S+)*)$", status, re.M)
        self.assertIsNotNone(validsig, status)
        self.assertEqual(validsig[1].split()[-1], SIGNING_KEY_FINGERPRINT)

    def test_the_signed_list_names_exactly_the_published_addresses(self):
        status = self.verify(SIGNED_LIST.read_bytes())
        self.assertIn("[GNUPG:] GOODSIG", status)
        plaintext = re.sub(r"^\[GNUPG:\].*$", "", status, flags=re.M)
        for guid, address in OWNER_ADDRESSES.items():
            with self.subTest(guid=guid):
                self.assertIn(address, plaintext)
        found = set(re.findall(r"\b(?:sp1|bc1)[02-9ac-hj-np-z]{20,}\b|\b[48][1-9A-HJ-NP-Za-km-z]{94}\b", plaintext))
        self.assertEqual(found, set(OWNER_ADDRESSES.values()))

    def test_a_tampered_list_fails_verification(self):
        signed = SIGNED_LIST.read_bytes()
        address = OWNER_ADDRESSES["monero"].encode()
        tampered = signed.replace(address, address[:-1] + (b"j" if address[-1:] != b"j" else b"k"))
        self.assertNotEqual(tampered, signed)
        status = self.verify(tampered)
        self.assertNotIn("[GNUPG:] GOODSIG", status)
        self.assertNotIn("[GNUPG:] VALIDSIG", status)


class ValidatorTest(unittest.TestCase):
    def assertRejected(self, validate, address):
        with self.assertRaises(donations.InvalidAddress, msg=address):
            validate(address)

    def test_every_single_character_typo_is_rejected(self):
        cases = [
            (donations.validate_silent_payment, "bitcoin-silent-payments", "qpzry9x8gf2tvdw0s3jn54khce6mua7l"),
            (donations.validate_bitcoin, "bitcoin", "qpzry9x8gf2tvdw0s3jn54khce6mua7l"),
            (donations.validate_monero, "monero", "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"),
        ]
        for validate, guid, alphabet in cases:
            for position, typo in single_character_typos(OWNER_ADDRESSES[guid], alphabet):
                with self.subTest(guid=guid, position=position):
                    self.assertRejected(validate, typo)

    def test_an_address_of_another_kind_is_rejected(self):
        self.assertRejected(donations.validate_bitcoin, OWNER_ADDRESSES["bitcoin-silent-payments"])
        self.assertRejected(donations.validate_silent_payment, OWNER_ADDRESSES["bitcoin"])
        self.assertRejected(donations.validate_monero, OWNER_ADDRESSES["bitcoin"])
        self.assertRejected(donations.validate_bitcoin, OWNER_ADDRESSES["monero"])

    def test_malformed_and_testnet_addresses_are_rejected(self):
        for validate, address in [
            (donations.validate_bitcoin, ""),
            (donations.validate_bitcoin, "tb1pqqqqp399et2xygdj5xreqhjjvcmzhxw4aywxecjdzew6hylgvsesf3hn0c"),
            (donations.validate_bitcoin, "bc1Pykga6j933ss43xmad2layn3ln99e29r9s2t8rwmmrn5f98p2x92sz42fep"),
            (donations.validate_bitcoin, "bc1pykga6j933ss43xmad2layn3ln99e29r9s2t8rwmmrn5f98p2x92sz42fep\x00"),
            (donations.validate_bitcoin, "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kemeawh"),
            (donations.validate_bitcoin, "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqh2y7hd"),
            (donations.validate_silent_payment, ""),
            (donations.validate_silent_payment, "t" + OWNER_ADDRESSES["bitcoin-silent-payments"]),
            (donations.validate_monero, ""),
            (donations.validate_monero, OWNER_ADDRESSES["monero"][:-1]),
            (donations.validate_monero, OWNER_ADDRESSES["monero"] + "1"),
            (donations.validate_monero, "0" + OWNER_ADDRESSES["monero"][1:]),
        ]:
            with self.subTest(address=address):
                self.assertRejected(validate, address)

    def test_bip350_reference_addresses_are_accepted(self):
        for address in [
            "BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4",
            "bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3",
            "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0",
        ]:
            with self.subTest(address=address):
                self.assertIsNone(donations.validate_bitcoin(address))

    def test_keccak256_matches_reference_digests(self):
        self.assertEqual(
            donations.keccak256(b"").hex(),
            "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470",
        )
        self.assertEqual(
            donations.keccak256(b"abc").hex(),
            "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45",
        )
        self.assertEqual(len(donations.keccak256(b"x" * 136)), 32)


class LoadDonationAddressesTest(unittest.TestCase):
    def write_funding(self, channels) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "funding.json"
        path.write_text(json.dumps({"funding": {"channels": channels}}), encoding="utf-8")
        return path

    def test_a_missing_channel_is_named_in_the_error(self):
        path = self.write_funding(
            [{"guid": guid, "type": "other", "address": address}
             for guid, address in OWNER_ADDRESSES.items() if guid != "monero"]
        )
        with self.assertRaisesRegex(donations.InvalidAddress, "'monero' is missing"):
            donations.load_donation_addresses(path)

    def test_an_invalid_address_is_named_by_its_channel(self):
        channels = [{"guid": guid, "type": "other", "address": address} for guid, address in OWNER_ADDRESSES.items()]
        channels[1]["address"] = OWNER_ADDRESSES["monero"]
        with self.assertRaisesRegex(donations.InvalidAddress, "'bitcoin'"):
            donations.load_donation_addresses(self.write_funding(channels))


if __name__ == "__main__":
    unittest.main()
