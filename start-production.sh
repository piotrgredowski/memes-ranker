#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    source .env
    echo "Loaded .env file"
else
    echo "Warning: .env file not found"
fi

# Initialize database if needed
echo "Initializing database..."
uv run python setup_db.py

# Start the application
echo "Starting application on port ${APP_PORT:-8000}..."
uv run python -m gunicorn app.main:app -c gunicorn.conf.py &

# Start nginx container with the same port
echo "Starting nginx proxy..."
docker run -d -p 40999:80 -e APP_PORT=${APP_PORT:-8000} --name memes-nginx simple-nginx
echo "Application started!"
echo "App: http://localhost:${APP_PORT:-8000}"
echo "Nginx: http://localhost:80"
