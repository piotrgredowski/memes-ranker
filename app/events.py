"""Event system for real-time updates in memes-ranker application."""

from enum import Enum
from typing import Any, Dict
from dataclasses import dataclass, asdict
import json


class EventType(str, Enum):
    """WebSocket event types for real-time updates."""

    # Session events
    SESSION_CREATED = "session_created"
    SESSION_STARTED = "session_started"
    SESSION_FINISHED = "session_finished"

    # Meme events
    MEMES_POPULATED = "memes_populated"

    # Rating events
    NEW_RATING = "new_rating"
    STATS_UPDATED = "stats_updated"

    # Connection events
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"


@dataclass
class Event:
    """Base event class for WebSocket messages."""

    type: EventType
    data: Dict[str, Any]
    timestamp: str = None

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Create event from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class EventBroadcaster:
    """Handles event broadcasting to WebSocket connections."""

    def __init__(self):
        self.websocket_manager = None

    def set_websocket_manager(self, manager):
        """Set the WebSocket manager instance."""
        self.websocket_manager = manager

    async def broadcast_session_event(
        self, event_type: EventType, session_data: Dict[str, Any]
    ):
        """Broadcast session-related events."""
        if not self.websocket_manager:
            return

        event = Event(type=event_type, data=session_data)

        # Broadcast to both admin and users
        await self.websocket_manager.broadcast_to_group("admin", event.to_json())
        await self.websocket_manager.broadcast_to_group("users", event.to_json())

    async def broadcast_rating_event(
        self, event_type: EventType, rating_data: Dict[str, Any]
    ):
        """Broadcast rating-related events."""
        if not self.websocket_manager:
            return

        event = Event(type=event_type, data=rating_data)

        # Rating events mainly for admin dashboard
        await self.websocket_manager.broadcast_to_group("admin", event.to_json())

    async def broadcast_stats_update(self, stats_data: Dict[str, Any]):
        """Broadcast statistics updates."""
        if not self.websocket_manager:
            return

        event = Event(type=EventType.STATS_UPDATED, data=stats_data)

        # Stats updates for admin dashboard
        await self.websocket_manager.broadcast_to_group("admin", event.to_json())

    async def broadcast_memes_populated(self, meme_count: int):
        """Broadcast when memes are populated."""
        if not self.websocket_manager:
            return

        event = Event(type=EventType.MEMES_POPULATED, data={"meme_count": meme_count})

        # Meme population events for admin dashboard
        await self.websocket_manager.broadcast_to_group("admin", event.to_json())


# Global event broadcaster instance
event_broadcaster = EventBroadcaster()
