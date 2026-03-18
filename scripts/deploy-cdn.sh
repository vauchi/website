#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Deploy signed content to cdn.vauchi.app via rsync over SSH.
#
# CI variables required:
#   CDN_HOST          - SSH host (e.g., cdn.vauchi.app or VPS IP)
#   CDN_USER          - SSH user (e.g., deploy)
#   CDN_SSH_KEY       - SSH private key (protected, masked)
#   CDN_CONTENT_PATH  - Remote path (default: /var/www/cdn.vauchi.app/v1)
#
# Usage:
#   scripts/deploy-cdn.sh <content-dir>
#   scripts/deploy-cdn.sh public/app-files

set -euo pipefail

CONTENT_DIR="${1:?Usage: deploy-cdn.sh <content-dir>}"
CDN_HOST="${CDN_HOST:?CDN_HOST not set}"
CDN_USER="${CDN_USER:-deploy}"
CDN_CONTENT_PATH="${CDN_CONTENT_PATH:-/var/www/cdn.vauchi.app/v1}"

if [ ! -d "$CONTENT_DIR" ]; then
    echo "ERROR: Content directory not found: $CONTENT_DIR"
    exit 1
fi

if [ ! -f "$CONTENT_DIR/manifest.json" ]; then
    echo "ERROR: manifest.json not found in $CONTENT_DIR"
    exit 1
fi

if [ ! -f "$CONTENT_DIR/manifest.json.sig" ]; then
    echo "WARNING: manifest.json.sig not found — content is unsigned"
fi

echo "Deploying content to ${CDN_USER}@${CDN_HOST}:${CDN_CONTENT_PATH}"
echo "  Source: $CONTENT_DIR"
echo "  Files:"
find "$CONTENT_DIR" -type f | sort | while read -r f; do
    echo "    $(basename "$f") ($(wc -c < "$f" | tr -d ' ') bytes)"
done

# Set up SSH key if provided via CI variable
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
if [ -n "${CDN_SSH_KEY:-}" ]; then
    SSH_KEY_FILE=$(mktemp)
    echo "$CDN_SSH_KEY" > "$SSH_KEY_FILE"
    chmod 600 "$SSH_KEY_FILE"
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY_FILE"
    # shellcheck disable=SC2064
    trap "rm -f '$SSH_KEY_FILE'" EXIT
fi

# Ensure remote directory exists
# shellcheck disable=SC2086
ssh $SSH_OPTS "${CDN_USER}@${CDN_HOST}" "mkdir -p ${CDN_CONTENT_PATH}"

# Rsync content (atomic: deploy to temp, then swap)
REMOTE_TEMP="${CDN_CONTENT_PATH}.new"
# shellcheck disable=SC2086
ssh $SSH_OPTS "${CDN_USER}@${CDN_HOST}" "rm -rf ${REMOTE_TEMP} && mkdir -p ${REMOTE_TEMP}"

# shellcheck disable=SC2086
rsync -avz --delete \
    -e "ssh $SSH_OPTS" \
    "${CONTENT_DIR}/" \
    "${CDN_USER}@${CDN_HOST}:${REMOTE_TEMP}/"

# Atomic swap
# shellcheck disable=SC2086
ssh $SSH_OPTS "${CDN_USER}@${CDN_HOST}" \
    "mv ${CDN_CONTENT_PATH} ${CDN_CONTENT_PATH}.old 2>/dev/null || true; \
     mv ${REMOTE_TEMP} ${CDN_CONTENT_PATH}; \
     rm -rf ${CDN_CONTENT_PATH}.old"

echo "Deploy complete: https://cdn.vauchi.app/v1/manifest.json"
