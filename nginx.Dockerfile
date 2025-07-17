FROM nginx:alpine

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy nginx configuration template
COPY nginx-simple.conf /etc/nginx/nginx.conf.template

# Copy static files (if you want nginx to serve them)
COPY static/ /usr/share/nginx/html/static/

# Set default app port if not provided
ENV APP_PORT=8000

# Expose port 80
EXPOSE 80

# Start nginx with environment variable substitution
CMD envsubst '${APP_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;'
