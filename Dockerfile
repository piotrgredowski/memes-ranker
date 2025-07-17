# Production FastAPI application with built-in virtual environment
FROM python:3.13-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt ./

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    uv pip install --no-cache -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p data logs static/memes static/js static/css templates && \
    chown -R appuser:appuser /app

# Don't switch to non-root user yet - entrypoint script will handle it
# USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/session/status || exit 1

# Default command - run entrypoint script
CMD ["/app/docker-entrypoint.sh"]
