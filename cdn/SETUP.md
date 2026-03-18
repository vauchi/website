<!-- SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# cdn.vauchi.app Setup Guide

Self-hosted Nginx serving signed content bundles (locales, themes, networks).

## DNS

A record: `cdn.vauchi.app` → VPS IP

## VPS Setup

### 1. TLS Certificate

```bash
sudo certbot certonly --standalone -d cdn.vauchi.app
```

### 2. Nginx Config

```bash
sudo cp cdn/nginx-cdn.conf /etc/nginx/sites-available/cdn.vauchi.app.conf
sudo ln -s /etc/nginx/sites-available/cdn.vauchi.app.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Content Directory

```bash
sudo mkdir -p /var/www/cdn.vauchi.app/v1
sudo chown deploy:deploy /var/www/cdn.vauchi.app
```

### 4. Deploy User

```bash
sudo useradd -m -s /bin/bash deploy
# Add SSH key from GitLab CI variable CDN_SSH_KEY
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
# paste public key into /home/deploy/.ssh/authorized_keys
```

## Content Signing (One-Time)

```bash
pip install PyNaCl
python scripts/sign-manifest.py --generate-key --key-dir keys/

# Output:
#   keys/content-signing.key  → store as CI variable CONTENT_SIGNING_KEY (protected, masked)
#   keys/content-signing.pub  → embed in vauchi-core for client verification
```

**NEVER commit `keys/content-signing.key` to git.**

## GitLab CI Variables

| Variable | Scope | Protected | Masked | Value |
|----------|-------|-----------|--------|-------|
| `CDN_HOST` | website | yes | no | VPS IP or `cdn.vauchi.app` |
| `CDN_USER` | website | yes | no | `deploy` |
| `CDN_SSH_KEY` | website | yes | yes | SSH private key for deploy user |
| `CONTENT_SIGNING_KEY` | website | yes | yes | Base64 Ed25519 private key from `keys/content-signing.key` |

## Manual Deploy

```bash
# Build content
python scripts/build-manifest.py --output public/app-files --base-url https://cdn.vauchi.app/v1/

# Sign manifest
python scripts/sign-manifest.py --manifest public/app-files/manifest.json \
    --private-key keys/content-signing.key

# Deploy
CDN_HOST=cdn.vauchi.app scripts/deploy-cdn.sh public/app-files
```

## Verify

```bash
curl -s https://cdn.vauchi.app/v1/manifest.json | python -m json.tool
curl -s https://cdn.vauchi.app/health
```

## Privacy Checklist

- [x] Anonymized logs (timestamp, status, bytes, URI only)
- [x] No ETag (tracking prevention)
- [x] No Set-Cookie
- [x] No Server version disclosure
- [x] TLS 1.3 only
- [x] CORS restricted to vauchi.app
- [x] Immutable cache headers on versioned content
- [x] Ed25519 manifest signatures
