#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sign a content manifest with Ed25519.

Reads the manifest JSON, produces a detached signature file.
The signature covers the canonical JSON (sorted keys, no trailing whitespace).

Usage:
    # Generate keypair (one-time setup)
    python scripts/sign-manifest.py --generate-key --key-dir keys/

    # Sign a manifest
    python scripts/sign-manifest.py --manifest public/app-files/manifest.json \
        --private-key keys/content-signing.key

    # Verify a signature
    python scripts/sign-manifest.py --verify --manifest public/app-files/manifest.json \
        --signature public/app-files/manifest.json.sig \
        --public-key keys/content-signing.pub

Requires: pip install PyNaCl
"""

# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

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
    """Produce canonical JSON bytes (sorted keys, compact, UTF-8)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


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

    print(f"Generated Ed25519 keypair:")
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
    """Sign a manifest file, write .sig alongside it."""
    # Load private key
    key_b64 = private_key_path.read_text().strip()
    key_bytes = base64.b64decode(key_b64)
    signing_key = SigningKey(key_bytes)

    # Load and canonicalize manifest
    with open(manifest_path) as f:
        manifest = json.load(f)
    canonical = canonical_json(manifest)

    # Sign
    signed = signing_key.sign(canonical)
    signature = signed.signature

    # Write detached signature (base64)
    sig_path = manifest_path.parent / (manifest_path.name + ".sig")
    sig_path.write_text(base64.b64encode(signature).decode("ascii") + "\n")

    print(f"Signed: {manifest_path}")
    print(f"Signature: {sig_path}")
    print(f"Canonical JSON size: {len(canonical)} bytes")


def verify_signature(
    manifest_path: Path, sig_path: Path, public_key_path: Path
) -> None:
    """Verify a manifest signature."""
    # Load public key
    key_b64 = public_key_path.read_text().strip()
    key_bytes = base64.b64decode(key_b64)
    verify_key = VerifyKey(key_bytes)

    # Load and canonicalize manifest
    with open(manifest_path) as f:
        manifest = json.load(f)
    canonical = canonical_json(manifest)

    # Load signature
    sig_b64 = sig_path.read_text().strip()
    signature = base64.b64decode(sig_b64)

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
    parser.add_argument("--signature", help="Signature file (for verification)")
    parser.add_argument("--verify", action="store_true", help="Verify mode")
    args = parser.parse_args()

    if args.generate_key:
        generate_keypair(Path(args.key_dir))
        return

    if args.verify:
        if not all([args.manifest, args.signature, args.public_key]):
            parser.error("--verify requires --manifest, --signature, --public-key")
        verify_signature(Path(args.manifest), Path(args.signature), Path(args.public_key))
        return

    if args.manifest and args.private_key:
        sign_manifest(Path(args.manifest), Path(args.private_key))
        return

    parser.print_help()


if __name__ == "__main__":
    main()