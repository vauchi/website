FROM nginx:alpine AS base

# Patch all OS packages to fix container scan CVEs (zlib, libpng, etc.)
RUN apk update && apk upgrade --no-cache && rm -rf /var/cache/apk/*

# Build stage — generate locale HTML from templates + i18n
FROM base AS build
RUN apk add --no-cache python3 py3-jinja2
WORKDIR /build
COPY templates/ templates/
COPY i18n/ i18n/
COPY scripts/build-pages.py scripts/build-pages.py
COPY public/ public/
RUN python3 scripts/build-pages.py

# Final image
FROM base
COPY --from=build /build/public/ /usr/share/nginx/html/

# Use custom nginx config for SPA support
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
