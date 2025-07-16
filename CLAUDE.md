# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a fully functional FastAPI-based memes-ranker application with shadcn/ui components, SQLite database, and Docker deployment support. Users can rate memes on a scale of 0-10, with admin dashboard for session management and statistics.

## Development Setup

- **Python Version**: Requires Python >=3.13.0
- **Package Manager**: Uses uv for fast dependency management
- **Dependencies**: All project dependencies installed via uv

## Common Commands

### Database Setup

```bash
# Initialize database (run once before first use)
python setup_db.py

# The database will be created at: data/memes.db
```

### Development Commands

```bash
# Install dependencies (already done)
uv add <package-name>

# Run the application
uv run python run.py

# Run tests
uv run python tests/test_basic_flow.py

# Activate virtual environment
source .venv/bin/activate
```

## Project Structure

- `run.py` - Application entry point
- `setup_db.py` - Database initialization script
- `app/` - Main application code
  - `main.py` - FastAPI application with routes
  - `database.py` - Async SQLite database operations
  - `auth.py` - Admin authentication
  - `utils.py` - Utility functions (QR code, coolname)
- `static/` - Static files (CSS, JS, memes)
- `templates/` - HTML templates
- `tests/` - Integration tests
- `sql/schema.sql` - Database schema
- `data/` - Database storage directory

## Quick Start

1. **Initialize Database**: `uv run python setup_db.py`
1. **Start Application**: `uv run python run.py`
1. **Open Browser**: http://localhost:8000
1. **Admin Access**: http://localhost:8000/admin (password: admin123)

## Architecture Notes

This is a complete FastAPI application with:

- **Frontend**: shadcn/ui components with minimal JavaScript
- **Backend**: FastAPI with async SQLite database operations
- **Authentication**: JWT-based admin authentication
- **Session Management**: Cookie-based user sessions
- **Testing**: Integration tests for complete game flow
