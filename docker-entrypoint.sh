#!/bin/bash
set -e

echo "Starting memes-ranker production deployment..."

# Ensure data directory exists and has proper permissions
echo "Setting up data directory..."
mkdir -p /app/data /app/logs
chown -R appuser:appuser /app/data /app/logs
chmod 755 /app/data /app/logs

# Create cache directory for uv
mkdir -p /home/appuser/.cache/uv
chown -R appuser:appuser /home/appuser/.cache
chmod 755 /home/appuser/.cache

# Initialize database if needed as appuser
echo "Checking database initialization..."
runuser -u appuser -- /app/.venv/bin/python /app/init_db_prod.py

# Start the application as appuser
echo "Starting application with Gunicorn..."
exec runuser -u appuser -- /app/.venv/bin/python -m gunicorn app.main:app -c gunicorn.conf.py
