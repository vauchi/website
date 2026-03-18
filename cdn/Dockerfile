# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# CDN container for cdn.vauchi.app
# Serves signed content bundles (locales, themes, networks)

FROM nginx:alpine

# Copy Nginx CDN config
COPY cdn/nginx-cdn.conf /etc/nginx/conf.d/default.conf

# Content is mounted as a volume, not baked in — CI deploys content
# separately via rsync to /var/www/cdn.vauchi.app on the host.
# This container only provides the Nginx config.

EXPOSE 80
