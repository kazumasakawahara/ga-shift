"""Agent communication models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of agent messages."""

    REQUEST = "request"
    RESPONSE = "response"
    PROGRESS = "progress"
    ERROR = "error"


class AgentMessage(BaseModel):
    """Message passed between agents."""

    sender: str
    receiver: str
    msg_type: MessageType
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
