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

# Final image — run as non-root nginx user
FROM base
RUN apk add --no-cache python3 supervisor && \
    mkdir -p /var/log/vauchi /var/log/supervisor /tmp /app /etc/supervisor/conf.d && \
    chown -R nginx:nginx /var/log/vauchi /var/log/supervisor /tmp /app /usr/share/nginx/html /etc/nginx/conf.d /etc/supervisor /var/cache/nginx

# Redirect nginx pid and logs to paths writable by the nginx user.
RUN sed -i -E 's|^[[:space:]]*pid[[:space:]]+/[^;]+;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf && \
    sed -i -E 's|^[[:space:]]*error_log[[:space:]]+/var/log/nginx/error\.log[^;]*;|error_log /var/log/vauchi/nginx.log warn;|' /etc/nginx/nginx.conf && \
    sed -i -E 's|^[[:space:]]*access_log[[:space:]]+/var/log/nginx/access\.log[^;]*;|access_log /var/log/vauchi/nginx-access.log main;|' /etc/nginx/nginx.conf

# Metrics collector
WORKDIR /app
COPY --chown=nginx:nginx metrics-collector/collector.py /app/collector.py
COPY --chown=nginx:nginx metrics-collector/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Static site and nginx config
COPY --from=build --chown=nginx:nginx /build/public/ /usr/share/nginx/html/
COPY --chown=nginx:nginx ./nginx.conf /etc/nginx/conf.d/default.conf

USER nginx
EXPOSE 80
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
