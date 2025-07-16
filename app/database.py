"""Database operations for memes-ranker application.

This module provides async SQLite database operations using aiosqlite.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite


class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: str = "data/memes.db"):
        """Initialize database connection manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with proper setup."""
        async with aiosqlite.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrency
            await conn.execute("PRAGMA journal_mode=WAL")
            # Enable foreign key constraints
            await conn.execute("PRAGMA foreign_keys=ON")
            # Set row factory for dict-like access
            conn.row_factory = aiosqlite.Row
            yield conn

    # User operations
    async def create_user(self, name: str, session_token: str) -> int:
        """Create a new user.

        Args:
            name: User's display name
            session_token: Unique session token

        Returns:
            User ID
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "INSERT INTO users (name, session_token) VALUES (?, ?)",
                (name, session_token),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_user_by_token(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get user by session token.

        Args:
            session_token: Session token to look up

        Returns:
            User data dict or None if not found
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM users WHERE session_token = ?", (session_token,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID.

        Args:
            user_id: User ID to look up

        Returns:
            User data dict or None if not found
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    # Meme operations
    async def create_meme(self, filename: str, path: str) -> int:
        """Create a new meme entry.

        Args:
            filename: Filename of the meme
            path: Path to the meme file

        Returns:
            Meme ID
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "INSERT INTO memes (filename, path) VALUES (?, ?)", (filename, path)
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_active_memes(self) -> List[Dict[str, Any]]:
        """Get all active memes.

        Returns:
            List of meme data dicts
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM memes WHERE active = TRUE ORDER BY created_at"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_meme_by_id(self, meme_id: int) -> Optional[Dict[str, Any]]:
        """Get meme by ID.

        Args:
            meme_id: Meme ID to look up

        Returns:
            Meme data dict or None if not found
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM memes WHERE id = ?", (meme_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_meme_active(self, meme_id: int, active: bool):
        """Set meme active status.

        Args:
            meme_id: Meme ID
            active: Whether meme should be active
        """
        async with self.get_connection() as conn:
            await conn.execute(
                "UPDATE memes SET active = ? WHERE id = ?", (active, meme_id)
            )
            await conn.commit()

    # Ranking operations
    async def create_ranking(self, user_id: int, meme_id: int, score: int) -> int:
        """Create or update a ranking.

        Args:
            user_id: User ID
            meme_id: Meme ID
            score: Score (0-10)

        Returns:
            Ranking ID
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """INSERT INTO rankings (user_id, meme_id, score)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, meme_id)
                   DO UPDATE SET score = excluded.score, created_at = CURRENT_TIMESTAMP""",
                (user_id, meme_id, score),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_user_rankings(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all rankings for a user.

        Args:
            user_id: User ID

        Returns:
            List of ranking data dicts
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT r.*, m.filename, m.path
                   FROM rankings r
                   JOIN memes m ON r.meme_id = m.id
                   WHERE r.user_id = ?
                   ORDER BY r.created_at""",
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_meme_rankings(self, meme_id: int) -> List[Dict[str, Any]]:
        """Get all rankings for a meme.

        Args:
            meme_id: Meme ID

        Returns:
            List of ranking data dicts
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT r.*, u.name
                   FROM rankings r
                   JOIN users u ON r.user_id = u.id
                   WHERE r.meme_id = ?
                   ORDER BY r.created_at""",
                (meme_id,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_meme_stats(self) -> List[Dict[str, Any]]:
        """Get ranking statistics for all memes.

        Returns:
            List of meme statistics
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT
                    m.id,
                    m.filename,
                    m.path,
                    COUNT(r.id) as ranking_count,
                    AVG(r.score) as average_score,
                    MIN(r.score) as min_score,
                    MAX(r.score) as max_score
                   FROM memes m
                   LEFT JOIN rankings r ON m.id = r.meme_id
                   WHERE m.active = TRUE
                   GROUP BY m.id
                   ORDER BY average_score DESC"""
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # Session operations
    async def create_session(self, name: str) -> int:
        """Create a new session.

        Args:
            name: Session name

        Returns:
            Session ID
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "INSERT INTO sessions (name) VALUES (?)", (name,)
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_active_session(self) -> Optional[Dict[str, Any]]:
        """Get currently active session.

        Returns:
            Session data dict or None if no active session
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE active = TRUE ORDER BY created_at DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def start_session(self, session_id: int):
        """Start a session.

        Args:
            session_id: Session ID to start
        """
        async with self.get_connection() as conn:
            # Deactivate all other sessions
            await conn.execute("UPDATE sessions SET active = FALSE")
            # Activate the target session
            await conn.execute(
                "UPDATE sessions SET active = TRUE, start_time = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,),
            )
            await conn.commit()

    async def end_session(self, session_id: int):
        """End a session.

        Args:
            session_id: Session ID to end
        """
        async with self.get_connection() as conn:
            await conn.execute(
                "UPDATE sessions SET active = FALSE, end_time = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,),
            )
            await conn.commit()


# Global database instance
db = Database()
