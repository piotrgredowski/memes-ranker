# Multi-stage build for Tailwind CSS compilation
# Stage 1: Build CSS with Node.js and Tailwind
FROM node:18-alpine AS css-builder

WORKDIR /app

# Copy package files
COPY package.json .
COPY tailwind.config.js .

# Install dependencies
RUN npm install

# Copy source files needed for Tailwind
COPY static/css/globals.css ./static/css/globals.css
COPY templates/ ./templates/
COPY static/js/ ./static/js/
COPY app/ ./app/

# Build CSS
RUN npm run build:css:prod

# Stage 2: Production FastAPI application
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

# Copy built CSS from the css-builder stage
COPY --from=css-builder --chown=appuser:appuser /app/static/css/output.css ./static/css/output.css

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Create necessary directories with proper ownership
RUN mkdir -p data logs static/memes static/js static/css templates && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/session/status || exit 1

# Default command - run entrypoint script
CMD ["/app/docker-entrypoint.sh"]
