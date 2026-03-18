#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sign a content manifest with Ed25519 (compatible with vauchi-core).

Embeds a hex-encoded Ed25519 signature in the manifest.json `signature` field.
The signature covers the canonical JSON of the manifest WITHOUT the signature field.

Canonical form: compact JSON, sorted keys, no trailing whitespace.

IMPORTANT: core/vauchi-core/src/content/integrity.rs verify_manifest_signature()
currently uses serde_json::to_vec (struct field order, HashMap non-deterministic).
Before enforcing signatures, core must be updated to use sorted-key canonical JSON
to match this signer. See: _private/docs/planning/todo/2026-03-09-runtime-assets-and-cdn.plan.md

Usage:
    # Generate keypair (one-time setup)
    python scripts/sign-manifest.py --generate-key --key-dir keys/

    # Sign a manifest (embeds signature in manifest.json)
    python scripts/sign-manifest.py --manifest public/app-files/manifest.json \
        --private-key keys/content-signing.key

    # Verify a signed manifest
    python scripts/sign-manifest.py --verify --manifest public/app-files/manifest.json \
        --public-key keys/content-signing.pub

Requires: pip install PyNaCl
"""

import argparse
import base64
import json
import sys
from pathlib import Path

try:
    from nacl.signing import SigningKey, VerifyKey
    from nacl.exceptions import BadSignatureError
except ImportError:
    print("Error: PyNaCl required. Install with: pip install PyNaCl")
    sys.exit(1)


def canonical_json(data: dict) -> bytes:
    """Produce canonical JSON bytes for signing.

    Uses sorted keys and compact separators to ensure deterministic output
    regardless of dict insertion order. This matches what core's verification
    should use (sorted-key canonical form).
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")


def generate_keypair(key_dir: Path) -> None:
    """Generate Ed25519 keypair for content signing."""
    key_dir.mkdir(parents=True, exist_ok=True)

    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key

    private_path = key_dir / "content-signing.key"
    public_path = key_dir / "content-signing.pub"

    # Private key: base64-encoded 32-byte seed
    private_path.write_text(
        base64.b64encode(bytes(signing_key)).decode("ascii") + "\n"
    )
    private_path.chmod(0o600)

    # Public key: base64-encoded 32-byte key
    public_path.write_text(
        base64.b64encode(bytes(verify_key)).decode("ascii") + "\n"
    )

    print("Generated Ed25519 keypair:")
    print(f"  Private key: {private_path}")
    print(f"  Public key:  {public_path}")
    print()
    print(f"Public key (base64): {base64.b64encode(bytes(verify_key)).decode('ascii')}")
    print()
    print("IMPORTANT:")
    print("  - Store private key as CI protected variable: CONTENT_SIGNING_KEY")
    print("  - Embed public key in vauchi-core for client-side verification")
    print("  - NEVER commit the private key to git")


def sign_manifest(manifest_path: Path, private_key_path: Path) -> None:
    """Sign a manifest, embed hex signature in the JSON."""
    # Load private key
    key_b64 = private_key_path.read_text().strip()
    key_bytes = base64.b64decode(key_b64)
    signing_key = SigningKey(key_bytes)

    # Load manifest
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Remove any existing signature for signing
    manifest.pop("signature", None)

    # Canonical JSON of manifest without signature
    canonical = canonical_json(manifest)

    # Sign
    signed = signing_key.sign(canonical)
    sig_hex = signed.signature.hex()

    # Embed hex signature in manifest
    manifest["signature"] = sig_hex

    # Write updated manifest with signature
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Signed: {manifest_path}")
    print(f"Signature: {sig_hex[:32]}...")
    print(f"Canonical JSON size: {len(canonical)} bytes")


def verify_signature(manifest_path: Path, public_key_path: Path) -> None:
    """Verify a manifest's embedded signature."""
    # Load public key
    key_b64 = public_key_path.read_text().strip()
    key_bytes = base64.b64decode(key_b64)
    verify_key = VerifyKey(key_bytes)

    # Load manifest
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Extract and remove signature
    sig_hex = manifest.pop("signature", None)
    if not sig_hex:
        print(f"FAIL: No signature field in {manifest_path}")
        sys.exit(1)

    signature = bytes.fromhex(sig_hex)

    # Canonical JSON of manifest without signature
    canonical = canonical_json(manifest)

    # Verify
    try:
        verify_key.verify(canonical, signature)
        print(f"PASS: Signature valid for {manifest_path}")
    except BadSignatureError:
        print(f"FAIL: Invalid signature for {manifest_path}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Ed25519 content manifest signing")
    parser.add_argument("--generate-key", action="store_true", help="Generate keypair")
    parser.add_argument("--key-dir", default="keys", help="Key directory")
    parser.add_argument("--manifest", help="Manifest file to sign/verify")
    parser.add_argument("--private-key", help="Private key file (for signing)")
    parser.add_argument("--public-key", help="Public key file (for verification)")
    parser.add_argument("--verify", action="store_true", help="Verify mode")
    args = parser.parse_args()

    if args.generate_key:
        generate_keypair(Path(args.key_dir))
        return

    if args.verify:
        if not all([args.manifest, args.public_key]):
            parser.error("--verify requires --manifest and --public-key")
        verify_signature(Path(args.manifest), Path(args.public_key))
        return

    if args.manifest and args.private_key:
        sign_manifest(Path(args.manifest), Path(args.private_key))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
