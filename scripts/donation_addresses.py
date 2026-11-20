#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Donation addresses: validated from funding.json, rendered as QR codes.

public/funding.json is the one place the addresses live. The support page
and the QR files are derived from it, so a mistyped or swapped address
fails the build instead of shipping in one place only (vauchi/private#1307).

Usage:
    python3 scripts/donation_addresses.py            # validate funding.json
    python3 scripts/donation_addresses.py --write-qr # regenerate the QR SVGs
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FUNDING_JSON = ROOT / "public" / "funding.json"
QR_DIR = ROOT / "public" / "support"


class InvalidAddress(ValueError):
    pass


_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_CONST = 1
_BECH32M_CONST = 0x2BC830A3


def _bech32_polymod(values: list[int]) -> int:
    generators = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for i, generator in enumerate(generators):
            if (top >> i) & 1:
                checksum ^= generator
    return checksum


def _bech32_decode(address: str, expected_hrp: str) -> tuple[int, list[int]]:
    """Return (checksum constant, 5-bit data without checksum)."""
    if address.lower() != address and address.upper() != address:
        raise InvalidAddress("mixed case")
    address = address.lower()
    hrp, separator, data = address.rpartition("1")
    if not separator or hrp != expected_hrp:
        raise InvalidAddress(f"prefix is not {expected_hrp}1")
    if len(data) < 7 or any(c not in _BECH32_CHARSET for c in data):
        raise InvalidAddress("not bech32 data")
    values = [_BECH32_CHARSET.index(c) for c in data]
    expanded_hrp = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
    constant = _bech32_polymod(expanded_hrp + values)
    if constant not in (_BECH32_CONST, _BECH32M_CONST):
        raise InvalidAddress("checksum mismatch")
    return constant, values[:-6]


def _five_to_eight_bits(values: list[int]) -> bytes:
    accumulator = 0
    bits = 0
    out = bytearray()
    for value in values:
        accumulator = (accumulator << 5) | value
        bits += 5
        while bits >= 8:
            bits -= 8
            out.append((accumulator >> bits) & 0xFF)
    if bits >= 5 or accumulator & ((1 << bits) - 1):
        raise InvalidAddress("non-zero padding")
    return bytes(out)


def validate_bitcoin(address: str) -> None:
    """A mainnet SegWit address: v0 in bech32, v1+ in bech32m (BIP-173, BIP-350)."""
    constant, data = _bech32_decode(address, "bc")
    if not data:
        raise InvalidAddress("no witness version")
    version, program = data[0], _five_to_eight_bits(data[1:])
    if version > 16 or not 2 <= len(program) <= 40:
        raise InvalidAddress("invalid witness program")
    if version == 0 and len(program) not in (20, 32):
        raise InvalidAddress("invalid v0 program length")
    if constant != (_BECH32_CONST if version == 0 else _BECH32M_CONST):
        raise InvalidAddress("wrong checksum variant for witness version")


def validate_silent_payment(address: str) -> None:
    """A mainnet v0 Silent Payments address: scan key + spend key (BIP-352)."""
    constant, data = _bech32_decode(address, "sp")
    if constant != _BECH32M_CONST:
        raise InvalidAddress("silent payment addresses use bech32m")
    if not data or data[0] != 0:
        raise InvalidAddress("not a v0 silent payment address")
    if len(_five_to_eight_bits(data[1:])) != 66:
        raise InvalidAddress("v0 carries two 33-byte public keys")


_KECCAK_ROUND_CONSTANTS = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_KECCAK_ROTATIONS = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]
_LANE_MASK = (1 << 64) - 1


def _rotate_left(lane: int, shift: int) -> int:
    return ((lane << shift) | (lane >> (64 - shift))) & _LANE_MASK if shift else lane


def _keccak_f1600(state: list[list[int]]) -> list[list[int]]:
    for round_constant in _KECCAK_ROUND_CONSTANTS:
        column = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
        delta = [column[(x - 1) % 5] ^ _rotate_left(column[(x + 1) % 5], 1) for x in range(5)]
        state = [[state[x][y] ^ delta[x] for y in range(5)] for x in range(5)]
        moved = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                moved[y][(2 * x + 3 * y) % 5] = _rotate_left(state[x][y], _KECCAK_ROTATIONS[x][y])
        state = [
            [moved[x][y] ^ (~moved[(x + 1) % 5][y] & moved[(x + 2) % 5][y]) for y in range(5)]
            for x in range(5)
        ]
        state[0][0] ^= round_constant
    return state


def keccak256(data: bytes) -> bytes:
    """Original Keccak-256 (Monero's hash), not NIST SHA3-256: the padding differs."""
    rate = 136
    padding = bytearray(rate - len(data) % rate)
    padding[0] |= 0x01
    padding[-1] |= 0x80
    padded = bytes(data) + bytes(padding)
    state = [[0] * 5 for _ in range(5)]
    for offset in range(0, len(padded), rate):
        block = padded[offset : offset + rate]
        for i in range(rate // 8):
            state[i % 5][i // 5] ^= int.from_bytes(block[8 * i : 8 * i + 8], "little")
        state = _keccak_f1600(state)
    return b"".join(state[i % 5][i // 5].to_bytes(8, "little") for i in range(4))


_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_BLOCK_SIZES = [0, -1, 1, 2, -1, 3, 4, 5, -1, 6, 7, 8]
_MONERO_NETWORK_BYTES = {18: "primary address", 42: "subaddress"}


def _monero_base58_decode(address: str) -> bytes:
    out = bytearray()
    for start in range(0, len(address), 11):
        block = address[start : start + 11]
        size = _BASE58_BLOCK_SIZES[len(block)]
        if size < 0:
            raise InvalidAddress("invalid base58 block length")
        number = 0
        for char in block:
            if char not in _BASE58_ALPHABET:
                raise InvalidAddress("not base58")
            number = number * 58 + _BASE58_ALPHABET.index(char)
        if number >= 1 << (8 * size):
            raise InvalidAddress("base58 block overflow")
        out += number.to_bytes(size, "big")
    return bytes(out)


def validate_monero(address: str) -> None:
    """A mainnet Monero primary address or subaddress with a valid checksum."""
    if len(address) != 95:
        raise InvalidAddress("mainnet standard addresses are 95 characters")
    raw = _monero_base58_decode(address)
    if raw[0] not in _MONERO_NETWORK_BYTES:
        raise InvalidAddress("not a mainnet primary address or subaddress")
    if keccak256(raw[:-4])[:4] != raw[-4:]:
        raise InvalidAddress("checksum mismatch")


DONATION_CHANNELS = {
    "bitcoin-silent-payments": validate_silent_payment,
    "bitcoin": validate_bitcoin,
    "monero": validate_monero,
}


def load_donation_addresses(funding_json: Path = FUNDING_JSON) -> dict[str, str]:
    """Return {channel guid: address} for every donation channel, validated."""
    channels = json.loads(funding_json.read_text(encoding="utf-8"))["funding"]["channels"]
    by_guid = {channel["guid"]: channel for channel in channels}
    addresses = {}
    for guid, validate in DONATION_CHANNELS.items():
        if guid not in by_guid:
            raise InvalidAddress(f"{funding_json}: channel {guid!r} is missing")
        address = by_guid[guid].get("address", "")
        try:
            validate(address)
        except InvalidAddress as error:
            raise InvalidAddress(f"{funding_json}: channel {guid!r}: {error}") from None
        addresses[guid] = address
    return addresses


def qr_svg_path(guid: str) -> Path:
    return QR_DIR / f"qr-{guid}.svg"


def render_qr_svg(address: str) -> str:
    """The QR code for an address, without qrencode's version comment.

    The comment names the qrencode version, which differs between hosts, so
    keeping it would make the committed file depend on who generated it.
    """
    result = subprocess.run(
        ["qrencode", "-t", "SVG", "--svg-path", "-l", "M", "-m", "4", "-s", "6", "-o", "-", address],
        check=True,
        capture_output=True,
        text=True,
    )
    return re.sub(r"<!--.*?-->\n?", "", result.stdout, flags=re.DOTALL)


def main() -> int:
    try:
        addresses = load_donation_addresses()
    except InvalidAddress as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if "--write-qr" in sys.argv:
        QR_DIR.mkdir(parents=True, exist_ok=True)
        for guid, address in addresses.items():
            qr_svg_path(guid).write_text(render_qr_svg(address), encoding="utf-8")
            print(f"  wrote {qr_svg_path(guid).relative_to(ROOT)}")
    print(f"  {len(addresses)} donation address(es) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
