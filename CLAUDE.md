# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project called "memes-ranker" configured with modern Python packaging using pyproject.toml. The project is in its initial stage with minimal code structure.

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

# Run Python scripts
uv run python hello.py
uv run python setup_db.py

# Activate virtual environment
source .venv/bin/activate
```

## Project Structure

- `hello.py` - Entry point with basic main function
- `pyproject.toml` - Project configuration and metadata
- `README.md` - Project documentation (currently empty)
- `setup_db.py` - Database initialization script
- `sql/schema.sql` - Database schema
- `app/database.py` - Async SQLite database operations
- `data/` - Database storage directory (created by setup_db.py)

## Architecture Notes

This is a minimal Python project structure. The main application logic is currently in `hello.py` with a simple main function. As the project grows, consider organizing code into proper modules and packages.
