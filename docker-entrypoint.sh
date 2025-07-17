#!/bin/bash
set -e

echo "Starting memes-ranker production deployment..."

# Ensure data directory exists and has proper permissions
echo "Setting up data directory..."
mkdir -p /app/data /app/logs
chown -R appuser:appuser /app/data /app/logs
chmod 755 /app/data /app/logs

# Debug: Check virtual environment
echo "Checking virtual environment..."
ls -la /app/.venv/bin/python || echo "Python not found in venv"
ls -la /app/.venv/bin/ | head -10

# Initialize database if needed as appuser
echo "Checking database initialization..."
runuser -u appuser -- python /app/init_db_prod.py

# Start the application as appuser
echo "Starting application with Gunicorn..."
echo "Using python: $(which python)"
exec runuser -u appuser -- /app/.venv/bin/python -m gunicorn app.main:app -c gunicorn.conf.py
