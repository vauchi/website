<!-- SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# cdn.vauchi.app Setup

Static content CDN deployed as a Docker container behind kamal-proxy on `bold-hopper-vps`.

## Architecture

```
kamal-proxy (:443, TLS via *.vauchi.app wildcard cert)
  └── cdn.vauchi.app → vauchi-cdn container (:80)
                          └── nginx:alpine serving /v1/*
```

Content is baked into the Docker image at build time (same pattern as the landing page).
Each content update produces a new image tag → deploy via `ci-deploy-service.sh`.

## DNS

A record: `cdn.vauchi.app` → same VPS as relay + landing.

The wildcard `*.vauchi.app` TLS cert already covers this subdomain.
kamal-proxy volume mounts handle cert provisioning — no certbot needed.

## Content Signing (One-Time)

```bash
pip install PyNaCl
python scripts/sign-manifest.py --generate-key --key-dir keys/
```

Store as GitLab CI variables:
- `CONTENT_SIGNING_KEY` (protected, masked) — base64 Ed25519 private key
- Embed `keys/content-signing.pub` in vauchi-core for client verification

**NEVER commit `keys/content-signing.key` to git.**

## CI Pipeline

The website CI builds and deploys the CDN image:

```
build:content (build-manifest.py)
  → sign:content (sign-manifest.py, main only)
    → build:cdn-docker (docker build -f cdn/Dockerfile)
      → deploy:cdn (ci-deploy-service.sh --service=cdn, manual gate)
```

## GitLab CI Variables

| Variable | Scope | Protected | Masked |
|----------|-------|-----------|--------|
| `CONTENT_SIGNING_KEY` | website | yes | yes |

Deploy uses existing `DEPLOY_SSH_PRIVATE_KEY` and `DEPLOY_HOST` from _private CI.

## Manual Deploy

```bash
# 1. Build content
python scripts/build-manifest.py --output public/app-files \
    --base-url https://cdn.vauchi.app/v1/

# 2. Sign
python scripts/sign-manifest.py --manifest public/app-files/manifest.json \
    --private-key keys/content-signing.key

# 3. Build Docker image
docker build -f cdn/Dockerfile -t registry.gitlab.com/vauchi/website/cdn:latest .
docker push registry.gitlab.com/vauchi/website/cdn:latest

# 4. Deploy via CI or _private pipeline
```

## Verify

```bash
curl -sI https://cdn.vauchi.app/health
curl -s https://cdn.vauchi.app/v1/manifest.json | python -m json.tool
```

## Privacy Checklist

- [x] TLS via kamal-proxy (wildcard `*.vauchi.app` cert)
- [x] Anonymized Nginx logs (timestamp, status, bytes, URI only)
- [x] No ETag (tracking prevention)
- [x] No Set-Cookie, no Server version
- [x] CORS headers
- [x] Immutable cache on versioned content
- [x] Ed25519 manifest signatures
- [x] Content baked into image (no runtime volume mounts needed)
