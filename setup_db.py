#!/usr/bin/env python3
"""Database setup script for memes-ranker application.

This script initializes the SQLite database with the required schema.
Run this script before starting the application for the first time.
"""

import sqlite3
import os
from pathlib import Path


def create_database(db_path: str = "data/memes.db"):
    """Create database and initialize schema."""
    # Create data directory if it doesn't exist
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # Read schema file
    schema_path = Path("sql/schema.sql")
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    # Create database connection
    conn = sqlite3.connect(db_path)

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


def main():
    """Main function to run database setup."""
    # Check if database already exists
    db_path = "data/memes.db"
    if os.path.exists(db_path):
        response = input(f"Database already exists at {db_path}. Recreate? (y/N): ")
        if response.lower() != "y":
            print("Database setup cancelled.")
            return
        os.remove(db_path)

    create_database(db_path)


if __name__ == "__main__":
    main()
