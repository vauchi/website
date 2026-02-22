<!-- SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

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

Static website explaining what Vauchi is and linking to app downloads. Also serves dynamic app content (locales, themes, networks) via JSON manifests with checksums.

## Structure

```
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

1. Create `app-files-src/locales/{lang}.json` following the schema
2. Run `python scripts/validate-content.py`
3. Run `python scripts/build-manifest.py`
4. Commit and push

### New Theme

Themes are managed in the [vauchi/themes](https://gitlab.com/vauchi/themes) repo.
See the themes repo README for contributing instructions.

### New Network

1. Edit `app-files-src/networks.json`
2. Validate and build as above

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
