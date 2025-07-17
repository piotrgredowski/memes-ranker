"""Database operations for memes-ranker application.

This module provides async SQLite database operations using aiosqlite.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from .logging_config import get_logger

logger = get_logger(__name__)


# Import will be added after database class to avoid circular import
_event_broadcaster = None


def get_event_broadcaster():
    """Get event broadcaster instance (lazy import to avoid circular dependency)."""
    global _event_broadcaster
    if _event_broadcaster is None:
        from .events import event_broadcaster

        _event_broadcaster = event_broadcaster
    return _event_broadcaster


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
    async def create_ranking(
        self, user_id: int, meme_id: int, score: int, session_id: int = None
    ) -> int:
        """Create or update a ranking.

        Args:
            user_id: User ID
            meme_id: Meme ID
            score: Score (0-10)
            session_id: Session ID (if None, uses active session)

        Returns:
            Ranking ID
        """
        # Get active session if not provided
        if session_id is None:
            active_session = await self.get_active_session()
            if not active_session:
                raise ValueError("No active session found")
            session_id = active_session["id"]

        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """INSERT INTO rankings (user_id, meme_id, score, session_id)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, meme_id, session_id)
                   DO UPDATE SET score = excluded.score, created_at = CURRENT_TIMESTAMP""",
                (user_id, meme_id, score, session_id),
            )
            await conn.commit()
            ranking_id = cursor.lastrowid

            # Broadcast new rating event
            try:
                from .events import EventType

                broadcaster = get_event_broadcaster()
                await broadcaster.broadcast_rating_event(
                    EventType.NEW_RATING,
                    {
                        "ranking_id": ranking_id,
                        "user_id": user_id,
                        "meme_id": meme_id,
                        "score": score,
                    },
                )

                # Also broadcast stats update
                meme_stats = await self.get_meme_stats()
                await broadcaster.broadcast_stats_update({"meme_stats": meme_stats})

            except Exception as e:
                logger.error(f"Failed to broadcast rating event: {e}")

            return ranking_id

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

    async def get_user_rankings_for_session(
        self, user_id: int, session_id: int
    ) -> List[Dict[str, Any]]:
        """Get all rankings for a user within a specific session.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            List of ranking data dicts from the current session only
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT r.*, m.filename, m.path
                   FROM rankings r
                   JOIN memes m ON r.meme_id = m.id
                   WHERE r.user_id = ? AND r.session_id = ?
                   ORDER BY r.created_at""",
                (user_id, session_id),
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
            session_id = cursor.lastrowid

            # Broadcast session created event
            try:
                from .events import EventType

                broadcaster = get_event_broadcaster()
                await broadcaster.broadcast_session_event(
                    EventType.SESSION_CREATED, {"id": session_id, "name": name}
                )
            except Exception as e:
                # Don't fail the operation if broadcasting fails
                logger.error("Failed to broadcast session created event", error=str(e))

            return session_id

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

            # Get session details for broadcasting
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session_row = await cursor.fetchone()

            if session_row:
                # Broadcast session started event
                try:
                    from .events import EventType

                    broadcaster = get_event_broadcaster()
                    session_data = dict(session_row)
                    await broadcaster.broadcast_session_event(
                        EventType.SESSION_STARTED, session_data
                    )
                except Exception as e:
                    logger.error(
                        "Failed to broadcast session started event", error=str(e)
                    )

    async def end_session(self, session_id: int):
        """End a session.

        Args:
            session_id: Session ID to end
        """
        async with self.get_connection() as conn:
            # Get session details before ending
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session_row = await cursor.fetchone()

            await conn.execute(
                "UPDATE sessions SET active = FALSE, end_time = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,),
            )
            await conn.commit()

            if session_row:
                # Broadcast session finished event
                try:
                    from .events import EventType

                    broadcaster = get_event_broadcaster()
                    session_data = dict(session_row)
                    session_data["active"] = False  # Update status
                    await broadcaster.broadcast_session_event(
                        EventType.SESSION_FINISHED, session_data
                    )
                except Exception as e:
                    logger.error(
                        "Failed to broadcast session finished event", error=str(e)
                    )

    async def get_total_vote_count(self) -> int:
        """Get total number of votes/rankings submitted.

        Returns:
            Total number of rankings in the database
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM rankings")
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def get_session_vote_count(self, session_id: int) -> int:
        """Get number of votes submitted for a specific session.

        Args:
            session_id: Session ID to get vote count for

        Returns:
            Number of votes for the session
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT COUNT(*) FROM rankings r
                   WHERE r.created_at >= (
                       SELECT start_time FROM sessions WHERE id = ? AND start_time IS NOT NULL
                   )""",
                (session_id,),
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def get_session_stats(self, session_id: int) -> dict:
        """Get comprehensive statistics for a specific session.

        Args:
            session_id: Session ID to get stats for

        Returns:
            Dictionary containing session statistics
        """
        async with self.get_connection() as conn:
            # Get session details
            session_cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session_row = await session_cursor.fetchone()

            if not session_row:
                return {}

            session = dict(session_row)

            # Count votes submitted during this session
            vote_cursor = await conn.execute(
                """SELECT COUNT(*) FROM rankings r
                   WHERE r.session_id = ?""",
                (session_id,),
            )
            vote_result = await vote_cursor.fetchone()
            vote_count = vote_result[0] if vote_result else 0

            # Get total number of active memes for expected votes calculation
            meme_cursor = await conn.execute(
                "SELECT COUNT(*) FROM memes WHERE active = TRUE"
            )
            meme_result = await meme_cursor.fetchone()
            meme_count = meme_result[0] if meme_result else 0

            # Get total unique users who have participated in this session
            users_cursor = await conn.execute(
                """SELECT COUNT(DISTINCT r.user_id) FROM rankings r
                   WHERE r.session_id = ?""",
                (session_id,),
            )
            users_result = await users_cursor.fetchone()
            unique_users_count = users_result[0] if users_result else 0

            return {
                "session": session,
                "vote_count": vote_count,
                "meme_count": meme_count,
                "unique_users_count": unique_users_count,
            }

    # Results reveal operations
    async def get_session_results(self, session_id: int) -> List[Dict[str, Any]]:
        """Get ranked results for a session with detailed statistics.

        Args:
            session_id: Session ID

        Returns:
            List of meme results ordered by average score (descending)
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT
                    m.id,
                    m.filename,
                    m.path,
                    COUNT(r.id) as vote_count,
                    AVG(r.score) as average_score,
                    MIN(r.score) as min_score,
                    MAX(r.score) as max_score,
                    CAST(SUBSTR(
                        GROUP_CONCAT(r.score ORDER BY r.score),
                        INSTR(GROUP_CONCAT(r.score ORDER BY r.score), ',') *
                        (COUNT(r.id) + 1) / 2 + 1,
                        INSTR(GROUP_CONCAT(r.score ORDER BY r.score), ',') - 1
                    ) AS REAL) as median_score
                FROM memes m
                LEFT JOIN rankings r ON m.id = r.meme_id AND r.session_id = ?
                WHERE m.active = TRUE
                GROUP BY m.id
                HAVING COUNT(r.id) > 0
                ORDER BY average_score DESC""",
                (session_id,),
            )
            rows = await cursor.fetchall()
            results = []
            for i, row in enumerate(rows):
                result = dict(row)
                result["position"] = len(rows) - i  # Position from last to first
                result["ranking"] = i + 1  # Ranking from 1st to last
                results.append(result)
            return results

    async def create_results_reveal(self, session_id: int) -> int:
        """Initialize results reveal for a session.

        Args:
            session_id: Session ID

        Returns:
            Results reveal ID
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """INSERT INTO results_reveal (session_id, current_position, is_complete)
                   VALUES (?, 0, FALSE)
                   ON CONFLICT(session_id) DO UPDATE SET
                   current_position = 0,
                   is_complete = FALSE,
                   updated_at = CURRENT_TIMESTAMP""",
                (session_id,),
            )
            await conn.commit()
            return cursor.lastrowid

    async def update_reveal_position(self, session_id: int, position: int):
        """Update current reveal position.

        Args:
            session_id: Session ID
            position: New position
        """
        async with self.get_connection() as conn:
            await conn.execute(
                """UPDATE results_reveal
                   SET current_position = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE session_id = ?""",
                (position, session_id),
            )
            await conn.commit()

    async def get_reveal_status(self, session_id: int) -> Dict[str, Any]:
        """Get current reveal status.

        Args:
            session_id: Session ID

        Returns:
            Reveal status dictionary
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT * FROM results_reveal WHERE session_id = ?""",
                (session_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {
                "session_id": session_id,
                "current_position": 0,
                "is_complete": False,
            }

    async def get_meme_detailed_stats(
        self, meme_id: int, session_id: int
    ) -> Dict[str, Any]:
        """Get detailed statistics for a meme in a session.

        Args:
            meme_id: Meme ID
            session_id: Session ID

        Returns:
            Detailed meme statistics
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT
                    m.id,
                    m.filename,
                    m.path,
                    COUNT(r.id) as vote_count,
                    AVG(r.score) as average_score,
                    MIN(r.score) as min_score,
                    MAX(r.score) as max_score,
                    GROUP_CONCAT(r.score ORDER BY r.score) as all_scores
                FROM memes m
                LEFT JOIN rankings r ON m.id = r.meme_id AND r.session_id = ?
                WHERE m.id = ? AND m.active = TRUE
                GROUP BY m.id""",
                (session_id, meme_id),
            )
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                # Calculate median and standard deviation
                if result["all_scores"]:
                    scores = [int(x) for x in result["all_scores"].split(",")]
                    scores.sort()
                    n = len(scores)
                    if n % 2 == 0:
                        result["median_score"] = (
                            scores[n // 2 - 1] + scores[n // 2]
                        ) / 2
                    else:
                        result["median_score"] = scores[n // 2]

                    # Calculate standard deviation
                    if n > 1:
                        mean = result["average_score"]
                        variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
                        result["std_deviation"] = variance**0.5
                    else:
                        result["std_deviation"] = 0
                else:
                    result["median_score"] = 0
                    result["std_deviation"] = 0

                return result
            return {}

    async def get_completed_sessions_with_results(self) -> List[Dict[str, Any]]:
        """Get all completed sessions that have results.

        Returns:
            List of completed sessions with metadata
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT
                    s.id,
                    s.name,
                    s.start_time,
                    s.end_time,
                    s.created_at,
                    COUNT(DISTINCT r.user_id) as participant_count,
                    COUNT(r.id) as total_votes,
                    COUNT(DISTINCT r.meme_id) as memes_rated,
                    rr.current_position,
                    rr.is_complete
                FROM sessions s
                LEFT JOIN rankings r ON s.id = r.session_id
                LEFT JOIN results_reveal rr ON s.id = rr.session_id
                WHERE s.active = FALSE AND s.end_time IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM rankings r2
                    WHERE r2.session_id = s.id
                )
                GROUP BY s.id
                ORDER BY s.end_time DESC""",
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_session_summary(self, session_id: int) -> Dict[str, Any]:
        """Get session summary for past results listing.

        Args:
            session_id: Session ID

        Returns:
            Session summary dictionary
        """
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """SELECT
                    s.id,
                    s.name,
                    s.start_time,
                    s.end_time,
                    s.created_at,
                    COUNT(DISTINCT r.user_id) as participant_count,
                    COUNT(r.id) as total_votes,
                    COUNT(DISTINCT r.meme_id) as memes_rated
                FROM sessions s
                LEFT JOIN rankings r ON s.id = r.session_id
                WHERE s.id = ?
                AND (s.start_time IS NULL OR r.created_at >= s.start_time)
                GROUP BY s.id""",
                (session_id,),
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {}

    async def complete_reveal(self, session_id: int):
        """Mark reveal as complete.

        Args:
            session_id: Session ID
        """
        async with self.get_connection() as conn:
            await conn.execute(
                """UPDATE results_reveal
                   SET is_complete = TRUE, updated_at = CURRENT_TIMESTAMP
                   WHERE session_id = ?""",
                (session_id,),
            )
            await conn.commit()


# Global database instance
db = Database()
