# Production FastAPI application using uv with Python base image
FROM python:3.13-slim

# Copy uv from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Change ownership of the app directory to appuser
RUN chown -R appuser:appuser /app

# Install dependencies into the system Python
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p data logs static/memes static/js static/css templates

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/session/status || exit 1

# Default command - run entrypoint script
CMD ["/app/docker-entrypoint.sh"]
