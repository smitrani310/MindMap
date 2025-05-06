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

def validate_message(msg_data: Dict[str, Any]) -> bool:
    """Validate message format and content."""
    try:
        # Check required fields
        required_fields = {'message_id', 'source', 'action', 'payload', 'timestamp'}
        if not all(field in msg_data for field in required_fields):
            return False

        # Validate field types
        if not isinstance(msg_data['message_id'], str):
            return False
        if not isinstance(msg_data['source'], str):
            return False
        if not isinstance(msg_data['action'], str):
            return False
        if not isinstance(msg_data['payload'], dict):
            return False
        if not isinstance(msg_data['timestamp'], (int, float)):
            return False

        # Validate action type
        valid_actions = {
            'canvas_click', 'canvas_dblclick', 'canvas_contextmenu',
            'new_node', 'create_node', 'edit_node', 'delete', 'delete_node', 'pos', 'reparent',
            'center_node', 'select_node', 'undo', 'redo'
        }
        if msg_data['action'] not in valid_actions:
            return False

        # Validate source
        valid_sources = {'frontend', 'backend'}
        if msg_data['source'] not in valid_sources:
            return False

        return True
    except Exception:
        return False

def create_response_message(original_message: Message, status: str, error: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> Message:
    """Create a response message based on the original message."""
    response_payload = payload if payload is not None else {}
    
    # Add error to payload for failed messages
    if status == 'failed' and error:
        response_payload['error'] = error
        
    return Message(
        source='backend',
        action=f"{original_message.action}_response",
        payload=response_payload,
        message_id=str(uuid.uuid4()),
        timestamp=datetime.datetime.now().timestamp() * 1000,
        status=status,
        error=error
    ) 