<!-- SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

> **Mirror:** This repo is a read-only mirror of [gitlab.com/vauchi/website](https://gitlab.com/vauchi/website). Please open issues and merge requests there.

[![Pipeline](https://img.shields.io/endpoint?url=https://vauchi.gitlab.io/website/badges/pipeline.json&label=pipeline)](https://gitlab.com/vauchi/website/-/pipelines)
[![REUSE](https://api.reuse.software/badge/gitlab.com/vauchi/website)](https://api.reuse.software/info/gitlab.com/vauchi/website)

# Vauchi Website

Landing page for Vauchi at [vauchi.app](https://vauchi.app).

## Requirements

### System Dependencies

| Tool | Required | Purpose |
|------|----------|---------|
| Python 3 | For build scripts | Content validation and manifest generation |
| Docker | For deployment | Containerization |
| Nginx | In container | Static file serving |

### Python Dependencies

```bash
pip install jsonschema
```

Required for `validate-content.py` schema validation.

## Overview

Static website explaining what Vauchi is and linking
to app downloads. Also serves dynamic app content
(locales, themes, networks) via JSON manifests with
checksums.

## Structure

```text
website/
├── public/                    # Static files served by nginx
│   ├── index.html             # Main landing page
│   ├── logo.png               # Brand logo
│   └── app-files/             # Generated app content (via build script)
│       ├── manifest.json      # Content manifest with checksums
│       ├── networks.json      # Network configurations
│       ├── locales/           # Localization files
│       └── themes/            # Theme definitions
│
├── app-files-src/             # Source content (before build)
│   ├── networks.json          # Network definitions
│   ├── locales/               # Language files (en.json, etc.)
│   └── schemas/               # JSON validation schemas
│       ├── networks.schema.json
│       ├── locales.schema.json
│       └── manifest.schema.json
│
├── scripts/                   # Build and validation scripts
│   ├── build-manifest.py      # Build manifest and copy content
│   └── validate-content.py    # Validate JSON against schemas
│
├── nginx.conf                 # Nginx server configuration
├── Dockerfile                 # Container definition
└── .gitlab-ci.yml             # CI/CD pipeline
```

## Development

### Local Preview

```bash
# Using Python
python -m http.server 8000 -d public

# Using Node
npx serve public
```

Then open http://localhost:8000

### Building App Content

Validate and build the app-files manifest:

```bash
# Validate content against schemas
python scripts/validate-content.py

# Build manifest and copy to public/app-files/
python scripts/build-manifest.py

# With options
python scripts/build-manifest.py --version 1.0.0 --output public/app-files
```

#### validate-content.py

Validates all JSON content files against their schemas:

```bash
python scripts/validate-content.py [--src app-files-src]

# Validates:
# - networks.json vs networks.schema.json
# - locales/*.json vs locales.schema.json
```

#### build-manifest.py

Generates content manifest with SHA-256 checksums:

```bash
python scripts/build-manifest.py [options]

Options:
  --version VERSION    Content version (default: 1.0.0)
  --output DIR         Output directory (default: public/app-files)
  --base-url URL       CDN URL (default: https://vauchi.app/app-files/)
  --src DIR            Source directory (default: app-files-src)
```

The generated `manifest.json` contains checksums for integrity verification by the mobile apps.

### Docker

```bash
# Build
docker build -t vauchi-website .

# Run
docker run -p 8080:80 vauchi-website
```

The image runs as the unprivileged `nginx` user; nginx logs and the metrics
JSONL files are written to `/var/log/vauchi`.

## Deployment

Deployed via Kamal to the same server as vauchi-relay. See [vauchi/infra](https://gitlab.com/vauchi/infra) for deployment config.

```bash
# From infra repo
kamal deploy -c config/deploy.vauchi-landing.yml
```

### CI/CD Pipeline

The `.gitlab-ci.yml` pipeline:

1. Validates content (`validate-content.py`)
2. Builds manifest (`build-manifest.py`)
3. Builds Docker image
4. Deploys via Kamal (on main branch)

## Adding Content

### New Locale

1. Add `{lang}.json` in the `locales` repo — the canonical source.
   This repo carries no locale copies; the build resolves the sibling
   checkout or the GitLab API and fails loudly otherwise.
2. Run `python scripts/build-manifest.py` here to verify resolution

### New Theme

Themes are managed in the [vauchi/themes](https://gitlab.com/vauchi/themes) repo.
See the themes repo README for contributing instructions.

### New Network

1. Edit `app-files-src/networks.json`
2. Validate and build as above

## Landing-Page Variant Test

The hero section randomly shows one of seven messaging variants (A/B/C/D/E/F/G)
to visitors and collects anonymous, aggregate feedback:

- **Variant selection** is random and session-scoped (`sessionStorage`).
- **DNT / GPC respected:** when a visitor sends a `Do Not Track` or
  `Global Privacy Control` signal, the variant is still shown but no
  anonymous metrics beacon is sent.
- **Metrics collected**: which variant was shown, how many primary CTA
  clicks occurred, and how long the page was visible (dwell time).
- **No cookies, no fingerprinting, no third-party scripts.** IP addresses
  are hashed with a daily salt and discarded; only the hash is stored.
- **Least-privilege runtime:** the container runs as the unprivileged
  `nginx` user, not as root.
- **Restricted logs:** raw JSONL log files are created with `0600`
  permissions and owned by the `nginx` user.

Source copy lives in `i18n/{lang}.json` under `hero.variant.{a-g}.*`.
The collector is `metrics-collector/collector.py`:

- `POST /beacon` — public beacon endpoint used by the page. Only POST is
  allowed; raw metrics are never exposed here.
- `GET /metrics/summary?days=7` — local debug aggregate stats (JSON), not
  exposed through nginx.
- It pushes aggregate gauges to the internal Prometheus Pushgateway
  (`vauchi-pushgateway:9091`) every 30 seconds.
- Raw beacon events are written to daily JSONL files
  (`metrics-YYYY-MM-DD.jsonl`) and auto-deleted after `LOG_RETENTION_DAYS`
  (default 30).

A provisioned Grafana dashboard is in `_private/infra/monitoring/grafana/provisioning/dashboards/json/landing-variants.json`.

## Related Repositories

| Repository | Description |
|------------|-------------|
| [vauchi/core](https://gitlab.com/vauchi/core) | Core Rust library |
| [vauchi/android](https://gitlab.com/vauchi/android) | Android app |
| [vauchi/ios](https://gitlab.com/vauchi/ios) | iOS app |
| [vauchi/docs](https://gitlab.com/vauchi/docs) | Documentation |
| [vauchi/assets](https://gitlab.com/vauchi/assets) | Brand assets, logos |
| [vauchi/infra](https://gitlab.com/vauchi/infra) | Deployment configs |

## Support the Project

Vauchi is open source and community-funded — no VC money, no data harvesting.

- [GitHub Sponsors](https://github.com/sponsors/vauchi)
- [Liberapay](https://liberapay.com/Vauchi/donate)
- [SUPPORTERS.md](https://gitlab.com/vauchi/vauchi/-/blob/main/SUPPORTERS.md) for sponsorship tiers

## License

MIT
