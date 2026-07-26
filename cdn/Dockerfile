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

# Bake build provenance so cdn.vauchi.app/build-info.json reports the exact
# built commit — the served-version signal used by `just deploy-status`, and
# parity with docs.vauchi.app / vauchi.app which already serve /build-info.json.
ARG BUILD_INFO='{"sha":"development","ref":"local","built":"unknown"}'
RUN printf '%s' "${BUILD_INFO}" > /usr/share/nginx/html/build-info.json

# Service label used by Kamal 2 to verify that the deployed image matches the
# intended service (prevents cross-service image mix-ups).
LABEL service="vauchi-cdn"

EXPOSE 80
