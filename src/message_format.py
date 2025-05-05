"""Message format and utilities for the Enhanced Mind Map application.

This module defines the standardized message format used for communication
between the frontend canvas and backend Python components.
"""

import json
import uuid
import datetime
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict

@dataclass
class Message:
    """Standardized message format for frontend-backend communication."""
    source: str  # Source of the message (e.g., 'network_canvas')
    action: str  # Action to perform (e.g., 'canvas_click', 'select_node')
    payload: Dict[str, Any]  # Message payload
    message_id: str  # Unique message identifier
    timestamp: float  # Unix timestamp in milliseconds
    status: str = 'pending'  # Message status: pending, processing, completed, failed
    error: Optional[str] = None  # Error message if status is 'failed'

    @classmethod
    def create(cls, source: str, action: str, payload: Dict[str, Any]) -> 'Message':
        """Create a new message with the given parameters."""
        return cls(
            source=source,
            action=action,
            payload=payload,
            message_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now().timestamp() * 1000
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a message from a dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create a message from a JSON string."""
        return cls.from_dict(json.loads(json_str))

def validate_message(data: Union[Dict[str, Any], str]) -> bool:
    """Validate if the given data matches the required message format."""
    try:
        if isinstance(data, str):
            data = json.loads(data)
        
        required_fields = {'source', 'action', 'payload', 'message_id', 'timestamp'}
        return all(field in data for field in required_fields)
    except (json.JSONDecodeError, TypeError):
        return False

def create_response_message(original_message: Message, status: str, error: Optional[str] = None) -> Message:
    """Create a response message based on the original message."""
    return Message(
        source='backend',
        action=f"{original_message.action}_response",
        payload=original_message.payload,
        message_id=str(uuid.uuid4()),
        timestamp=datetime.datetime.now().timestamp() * 1000,
        status=status,
        error=error
    ) 