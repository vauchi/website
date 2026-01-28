<!-- SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# CLAUDE.md - Website

Static website for vauchi project.

## Stack

- Static HTML/CSS
- Nginx for serving
- Docker for deployment

## Structure

- `public/` - Static files served by nginx
- `nginx.conf` - Server configuration
- `Dockerfile` - Container build

## Editing Rules

- Keep it simple - static files preferred
- Optimize images before adding
- Test locally: `docker build -t vauchi-web . && docker run -p 8080:80 vauchi-web`

## Deployment

See `Dockerfile` and `nginx.conf` for production setup.
