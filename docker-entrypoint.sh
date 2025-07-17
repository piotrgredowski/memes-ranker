#!/bin/bash
set -e

echo "Starting memes-ranker production deployment..."

# Initialize database if needed
echo "Checking database initialization..."
python /app/init_db_prod.py

# Start the application
echo "Starting application with Gunicorn..."
exec /app/.venv/bin/python -m gunicorn app.main:app -c gunicorn.conf.py
