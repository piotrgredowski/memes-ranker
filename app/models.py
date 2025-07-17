"""Data models for memes-ranker application."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import re


class FrontendLogEntry(BaseModel):
    """Frontend log entry model."""

    level: str = Field(..., description="Log level: debug, info, warn, error")
    message: str = Field(..., max_length=1000, description="Log message")
    timestamp: datetime = Field(..., description="Client timestamp")
    url: str = Field(..., max_length=500, description="Page URL")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent")
    session_id: Optional[str] = Field(None, max_length=100, description="Session ID")
    user_id: Optional[str] = Field(None, max_length=100, description="User ID")
    component: Optional[str] = Field(None, max_length=100, description="Component name")
    action: Optional[str] = Field(None, max_length=100, description="Action name")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    stack_trace: Optional[str] = Field(None, max_length=5000, description="Stack trace")

    @validator("level")
    def validate_level(cls, v):
        """Validate log level."""
        valid_levels = ["debug", "info", "warn", "error"]
        if v.lower() not in valid_levels:
            raise ValueError(f"Level must be one of: {valid_levels}")
        return v.lower()

    @validator("message")
    def validate_message(cls, v):
        """Sanitize log message."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        # Remove potential sensitive data patterns
        v = re.sub(
            r"(password|token|key|secret)=[^\s&]+", r"\1=***", v, flags=re.IGNORECASE
        )
        return v.strip()

    @validator("url")
    def validate_url(cls, v):
        """Validate and sanitize URL."""
        if not v:
            raise ValueError("URL is required")
        # Remove query parameters that might contain sensitive data
        v = re.sub(r"[?&](password|token|key|secret)=[^&]*", "", v, flags=re.IGNORECASE)
        return v

    @validator("metadata")
    def validate_metadata(cls, v):
        """Validate and sanitize metadata."""
        if v is None:
            return v

        # Limit metadata size
        if len(str(v)) > 2000:
            return {"error": "Metadata too large, truncated"}

        # Remove sensitive keys
        sensitive_keys = ["password", "token", "key", "secret", "auth", "credential"]
        if isinstance(v, dict):
            sanitized = {}
            for key, value in v.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    sanitized[key] = "***"
                else:
                    sanitized[key] = value
            return sanitized

        return v

    @validator("stack_trace")
    def validate_stack_trace(cls, v):
        """Validate stack trace."""
        if v and len(v) > 5000:
            return v[:5000] + "... (truncated)"
        return v


class FrontendLogBatch(BaseModel):
    """Batch of frontend log entries."""

    logs: List[FrontendLogEntry] = Field(..., max_items=50, description="Log entries")
    client_info: Optional[Dict[str, Any]] = Field(
        None, description="Client information"
    )

    @validator("logs")
    def validate_logs(cls, v):
        """Validate log entries."""
        if not v:
            raise ValueError("At least one log entry is required")
        if len(v) > 50:
            raise ValueError("Maximum 50 log entries per batch")
        return v


class SessionRequest(BaseModel):
    """Session creation request."""

    name: str = Field(..., min_length=1, max_length=100, description="Session name")

    @validator("name")
    def validate_name(cls, v):
        """Validate session name."""
        if not v or not v.strip():
            raise ValueError("Session name cannot be empty")
        return v.strip()


class RankingRequest(BaseModel):
    """Ranking submission request."""

    meme_id: int = Field(..., ge=1, description="Meme ID")
    score: int = Field(..., ge=0, le=10, description="Score (0-10)")

    @validator("score")
    def validate_score(cls, v):
        """Validate score range."""
        if not (0 <= v <= 10):
            raise ValueError("Score must be between 0 and 10")
        return v
