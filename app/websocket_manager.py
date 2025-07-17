"""WebSocket connection manager for real-time updates."""

import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from .logging_config import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        # Group connections by type (admin, users)
        self.connections: Dict[str, Set[WebSocket]] = {"admin": set(), "users": set()}

        # Track connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}

    async def connect(
        self, websocket: WebSocket, client_type: str, client_id: str = None
    ):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        # Add to appropriate group
        if client_type in self.connections:
            self.connections[client_type].add(websocket)

            # Store connection metadata
            self.connection_info[websocket] = {
                "type": client_type,
                "id": client_id,
                "connected_at": datetime.now().isoformat(),
            }

            logger.info(f"WebSocket connected: {client_type} client ({client_id})")

            # Send welcome message
            await self.send_personal_message(
                websocket,
                {
                    "type": "connection_established",
                    "data": {
                        "client_type": client_type,
                        "client_id": client_id,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
            )

            # Broadcast updated connection stats to admins
            await self.broadcast_connection_stats()
        else:
            logger.warning(f"Unknown client type: {client_type}")
            await websocket.close(code=1000)

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        # Find and remove from appropriate group
        for group_name, connections in self.connections.items():
            if websocket in connections:
                connections.remove(websocket)
                break

        # Remove metadata
        info = self.connection_info.pop(websocket, {})
        client_type = info.get("type", "unknown")
        client_id = info.get("id", "unknown")

        logger.info(f"WebSocket disconnected: {client_type} client ({client_id})")

        # Broadcast updated connection stats to admins
        await self.broadcast_connection_stats()

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send message to a specific WebSocket connection."""
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)

    async def broadcast_to_group(self, group: str, message: str):
        """Broadcast message to all connections in a group."""
        if group not in self.connections:
            logger.warning(f"Unknown group: {group}")
            return

        connections = self.connections[
            group
        ].copy()  # Copy to avoid modification during iteration

        # Send to all connections in parallel
        tasks = []
        for connection in connections:
            tasks.append(self._safe_send(connection, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send(self, websocket: WebSocket, message: str):
        """Safely send message to WebSocket, handling disconnections."""
        try:
            await websocket.send_text(message)
        except WebSocketDisconnect:
            await self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            await self.disconnect(websocket)

    async def broadcast_session_update(self, event_type: str, session_data: dict):
        """Broadcast session updates to all connected clients."""
        message = json.dumps(
            {
                "type": event_type,
                "data": session_data,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Broadcast to both admin and users
        await self.broadcast_to_group("admin", message)
        await self.broadcast_to_group("users", message)

    def get_connection_stats(self) -> dict:
        """Get current connection statistics."""
        return {
            "total_connections": sum(
                len(connections) for connections in self.connections.values()
            ),
            "admin_connections": len(self.connections["admin"]),
            "user_connections": len(self.connections["users"]),
            "groups": list(self.connections.keys()),
        }

    async def broadcast_connection_stats(self):
        """Broadcast current connection stats to admin clients."""
        from .database import db

        # Get connection stats
        stats = self.get_connection_stats()

        # Get vote stats from database
        try:
            # Get active session and its stats
            active_session = await db.get_active_session()
            if not active_session:
                return

            session_stats = await db.get_session_stats(active_session["id"])
            total_votes = session_stats.get("vote_count", 0)
            meme_count = session_stats.get("meme_count", 0)

            # Calculate expected votes (effective users × memes)
            # Use the higher of currently connected users or users who have already participated
            effective_users = max(
                stats["user_connections"], session_stats.get("unique_users_count", 0)
            )
            expected_votes = effective_users * meme_count

            # Combine stats
            combined_stats = {
                **stats,
                "total_votes": total_votes,
                "meme_count": meme_count,
                "expected_votes": expected_votes,
                "timestamp": datetime.now().isoformat(),
            }

            message = json.dumps({"type": "connection_stats", "data": combined_stats})

            # Only broadcast to admin connections
            await self.broadcast_to_group("admin", message)

        except Exception as e:
            logger.error(f"Error broadcasting connection stats: {e}")

    async def ping_all_connections(self):
        """Send ping to all connections to check health."""
        ping_message = json.dumps(
            {"type": "ping", "timestamp": datetime.now().isoformat()}
        )

        for group in self.connections:
            await self.broadcast_to_group(group, ping_message)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
