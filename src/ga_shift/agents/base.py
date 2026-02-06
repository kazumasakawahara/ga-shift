"""Base agent class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ga_shift.models.messages import AgentMessage, MessageType


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier."""

    def process(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a request and return results.

        Args:
            action: The action to perform.
            payload: Action-specific data.

        Returns:
            Result dictionary.

        Raises:
            ValueError: If action is not supported.
        """
        method_name = f"_handle_{action}"
        handler = getattr(self, method_name, None)
        if handler is None:
            raise ValueError(f"Agent '{self.name}' does not support action '{action}'")
        return handler(payload)

    def create_message(
        self,
        receiver: str,
        action: str,
        payload: dict[str, Any] | None = None,
        msg_type: MessageType = MessageType.REQUEST,
    ) -> AgentMessage:
        return AgentMessage(
            sender=self.name,
            receiver=receiver,
            msg_type=msg_type,
            action=action,
            payload=payload or {},
        )
