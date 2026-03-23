FROM nginx:alpine

# Patch all OS packages to fix container scan CVEs (zlib, libpng, etc.)
RUN apk update && apk upgrade --no-cache && rm -rf /var/cache/apk/*

# Copy static files
COPY ./public/ /usr/share/nginx/html/

# Use custom nginx config for SPA support
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
