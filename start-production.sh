#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    set -a  # automatically export all variables
    source .env
    set +a  # turn off automatic export
    echo "Loaded .env file"
    echo "APP_PORT=${APP_PORT}"
    echo "NGINX_PORT=${NGINX_PORT}"
else
    echo "Warning: .env file not found"
fi

# Initialize database if needed
echo "Initializing database..."
uv run python setup_db.py

# Start the application
echo "Starting application on port ${APP_PORT:-8000}..."
uv run python -m gunicorn app.main:app -c gunicorn.conf.py &

# Build nginx image if it doesn't exist
echo "Building nginx container..."
docker build -f nginx.Dockerfile -t simple-nginx . || echo "Warning: Failed to build nginx image"

# Clean up existing container if it exists
docker rm -f memes-nginx 2>/dev/null || true

# Start nginx container with the same port
echo "Starting nginx proxy..."
docker run -d -p ${NGINX_PORT:-40999}:80 -e APP_PORT=${APP_PORT:-8000} --name memes-nginx simple-nginx

echo "Application started!"
echo "App: http://localhost:${APP_PORT:-8000}"
echo "Nginx: http://localhost:${NGINX_PORT:-40999}"
