FROM nginx:alpine

# Copy static files
COPY ./public/ /usr/share/nginx/html/

# Use custom nginx config for SPA support
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
