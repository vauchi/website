# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# CDN container for cdn.vauchi.app
# Serves signed content bundles (locales, themes, networks)
# Deployed behind kamal-proxy (TLS via wildcard *.vauchi.app cert)

FROM nginx:alpine

# Patch all OS packages to fix container scan CVEs (zlib, libpng, etc.)
RUN apk update && apk upgrade --no-cache && rm -rf /var/cache/apk/*

# Privacy-hardened Nginx config (listen :80, kamal-proxy handles TLS)
COPY cdn/nginx-cdn.conf /etc/nginx/conf.d/default.conf

# Bake content into image at /usr/share/nginx/html/v1/
# Built by CI: build-manifest.py → sign-manifest.py → docker build
COPY public/app-files/ /usr/share/nginx/html/v1/

EXPOSE 80
