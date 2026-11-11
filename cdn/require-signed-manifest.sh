#!/bin/sh
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Refuses to let the CDN image ship a manifest without an Ed25519
# signature: apps reject such a manifest and get no content updates
# (vauchi/private#1244). Runs in kaniko's BusyBox shell, which has no
# Python or jq, so it checks the field's shape, not the signature.
set -eu

manifest="${1:?usage: require-signed-manifest.sh <manifest.json>}"

if [ ! -f "$manifest" ]; then
    echo "ERROR: $manifest does not exist" >&2
    exit 1
fi

if ! grep -Eq '"signature"[[:space:]]*:[[:space:]]*"[0-9a-f]{128}"' "$manifest"; then
    echo "ERROR: $manifest is unsigned; apps would reject every content update." >&2
    echo "The image must take public/app-files/ from sign:content." >&2
    exit 1
fi
