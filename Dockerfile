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

# Blog build stage — official zola image (glibc binary, can't run on
# alpine, so the build happens here and only the output is copied out)
FROM ghcr.io/getzola/zola:v0.22.1 AS blogbuild
COPY blog/ /blog/
RUN ["/bin/zola", "--root", "/blog", "build", "--output-dir", "/blog-out"]

# Blog CMS bundle (vauchi/private#822). Served from this image, not a
# CDN, so the admin page's CSP stays script-src 'self'. The tarball is the
# npm one; its sha512 matched the registry's integrity field when pinned.
FROM base AS cms
ARG SVELTIA_VERSION=0.237.0
ARG SVELTIA_SHA256=562ff1cda6003b3265a5d5ed429347d4e52b344e5954ef09e8849ec786c5c887
RUN wget -q -O /tmp/cms.tgz "https://registry.npmjs.org/@sveltia/cms/-/cms-${SVELTIA_VERSION}.tgz" \
    && echo "${SVELTIA_SHA256}  /tmp/cms.tgz" | sha256sum -c - \
    && tar -xzf /tmp/cms.tgz -C /tmp \
    && mkdir -p /cms/chunks \
    && cp /tmp/package/dist/sveltia-cms.js /cms/ \
    && cp /tmp/package/dist/chunks/*.js /cms/chunks/

# Final image — run as non-root nginx user
FROM base

# Install Python runtime, supervisor, pip, and create a venv for the waitlist API.
RUN apk add --no-cache python3 py3-pip supervisor \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && mkdir -p /var/log/vauchi /var/log/supervisor /tmp /app /data /etc/supervisor/conf.d \
    && chown -R nginx:nginx /var/log/vauchi /var/log/supervisor /tmp /app /data /usr/share/nginx/html /etc/nginx/conf.d /etc/supervisor /var/cache/nginx /opt/venv \
    && rm -rf /var/cache/apk/* /root/.cache/pip

ENV PATH="/opt/venv/bin:$PATH"

# Redirect nginx pid and logs to paths writable by the nginx user.
RUN sed -i -E 's|^[[:space:]]*pid[[:space:]]+/[^;]+;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf && \
    sed -i -E 's|^[[:space:]]*error_log[[:space:]]+/var/log/nginx/error\.log[^;]*;|error_log /var/log/vauchi/nginx.log warn;|' /etc/nginx/nginx.conf && \
    sed -i -E 's|^[[:space:]]*access_log[[:space:]]+/var/log/nginx/access\.log[^;]*;|access_log off;|' /etc/nginx/nginx.conf

WORKDIR /app

COPY --chown=nginx:nginx supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Waitlist API
COPY --chown=nginx:nginx waitlist /app/waitlist
COPY --chown=nginx:nginx i18n /app/waitlist/i18n
COPY --chown=nginx:nginx waitlist/supervisord.conf /etc/supervisor/conf.d/waitlist.conf
RUN /opt/venv/bin/pip install --no-cache-dir -r /app/waitlist/requirements.txt \
    && chown -R nginx:nginx /opt/venv

# Static site and nginx config
COPY --from=build --chown=nginx:nginx /build/public/ /usr/share/nginx/html/
COPY --from=blogbuild --chown=nginx:nginx /blog-out/ /usr/share/nginx/html/blog/
COPY --from=cms --chown=nginx:nginx /cms/ /usr/share/nginx/html/blog/admin/
COPY --chown=nginx:nginx ./nginx.conf /etc/nginx/conf.d/default.conf

# Service label used by Kamal 2 to verify that the deployed image matches the
# intended service (prevents cross-service image mix-ups).
LABEL service="vauchi-landing"

USER nginx
EXPOSE 80
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
