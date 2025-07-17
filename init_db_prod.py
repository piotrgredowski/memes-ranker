#!/usr/bin/env python3
"""Production database initialization script for memes-ranker application.

This script automatically initializes the SQLite database with the required schema
if it doesn't exist. Designed for production Docker deployments.
"""

import os
import sqlite3
from pathlib import Path


def init_database_if_needed(db_path: str = "/app/data/memes.db"):
    """Initialize database if it doesn't exist."""
    # Create data directory if it doesn't exist
    db_dir = Path(db_path).parent
    try:
        db_dir.mkdir(parents=True, exist_ok=True)
        print(f"Database directory created/verified at: {db_dir}")
    except PermissionError as e:
        print(f"Permission error creating directory {db_dir}: {e}")
        raise

    # Check if database already exists
    if os.path.exists(db_path):
        print(f"Database already exists at: {db_path}")
        return

    # Read schema file
    schema_path = Path("/app/sql/schema.sql")
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    # Test if we can create the database file
    try:
        # Create database connection
        conn = sqlite3.connect(db_path)
    except sqlite3.OperationalError as e:
        print(f"Cannot create database at {db_path}: {e}")
        print(f"Directory exists: {db_dir.exists()}")
        print(
            f"Directory permissions: {oct(os.stat(db_dir).st_mode)[-3:] if db_dir.exists() else 'N/A'}"
        )
        print(f"Current user: {os.getuid()}")
        print(f"Current group: {os.getgid()}")
        raise

    try:
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")

        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys=ON")

        # Execute schema
        conn.executescript(schema_sql)

        print(f"Database created successfully at: {db_path}")
        print("Schema initialized with tables: users, memes, rankings, sessions")

    except Exception as e:
        print(f"Error creating database: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Use environment variable for database path
    db_path = os.getenv("DATABASE_PATH", "/app/data/memes.db")
    init_database_if_needed(db_path)
