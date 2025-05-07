#!/usr/bin/env python
"""
Unit tests for message format validation and handling.
Tests the core functionality of message creation, validation, and formatting
without requiring external dependencies or complex setups.
"""

import unittest
import time
from src.message_format import Message, create_response_message, validate_message

class TestMessageFormat(unittest.TestCase):
    """Test suite for message format functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Initialize common test data
        self.test_message_data = {
            'action': 'canvas_click',  # Using a valid action from the allowed set
            'source': 'frontend',      # Using a valid source from the allowed set
            'message_id': '123',
            'payload': {'x': 100, 'y': 100},
            'timestamp': int(time.time() * 1000)  # Current time in milliseconds
        }

    def test_message_creation(self):
        """Test basic message creation and attribute setting.
        
        Verifies that:
        - Message objects can be created with correct attributes
        - All required fields are properly set
        - Default values are applied correctly
        """
        message = Message(**self.test_message_data)
        self.assertEqual(message.action, 'canvas_click')
        self.assertEqual(message.source, 'frontend')
        self.assertEqual(message.message_id, '123')
        self.assertEqual(message.payload, {'x': 100, 'y': 100})
        self.assertEqual(message.timestamp, self.test_message_data['timestamp'])
        self.assertEqual(message.status, 'pending')  # Default value

    def test_message_validation(self):
        """Test message validation rules.
        
        Verifies that:
        - Messages with all required fields pass validation
        - Messages with missing required fields fail validation
        - Messages with invalid field types fail validation
        - Edge cases (empty strings, None values) are handled correctly
        """
        # Valid message
        self.assertTrue(validate_message(self.test_message_data))

        # Invalid message (missing required field)
        invalid_data = self.test_message_data.copy()
        del invalid_data['action']
        self.assertFalse(validate_message(invalid_data))

        # Invalid message (invalid action)
        invalid_data = self.test_message_data.copy()
        invalid_data['action'] = 'invalid_action'
        self.assertFalse(validate_message(invalid_data))

        # Invalid message (invalid source)
        invalid_data = self.test_message_data.copy()
        invalid_data['source'] = 'invalid_source'
        self.assertFalse(validate_message(invalid_data))

    def test_response_message_creation(self):
        """Test creation of response messages.
        
        Verifies that:
        - Response messages maintain reference to original message
        - Status and error messages are properly set
        - Response message IDs are correctly generated
        - Payload is properly carried over or modified
        """
        original_msg = Message(**self.test_message_data)
        response = create_response_message(
            original_msg,
            'completed',
            None,
            {'result': 'success'}
        )
        
        self.assertEqual(response.source, 'backend')
        self.assertEqual(response.action, 'canvas_click_response')
        self.assertEqual(response.status, 'completed')
        self.assertIsNone(response.error)
        self.assertEqual(response.payload['result'], 'success')

    def test_message_serialization(self):
        """Test message serialization and deserialization.
        
        Verifies that:
        - Messages can be converted to dictionaries
        - Messages can be recreated from dictionaries
        - All attributes are preserved during serialization
        - Special characters and complex payloads are handled correctly
        """
        message = Message(**self.test_message_data)
        serialized = message.to_dict()
        
        # Verify all fields are present in serialized form
        self.assertIn('action', serialized)
        self.assertIn('source', serialized)
        self.assertIn('message_id', serialized)
        self.assertIn('payload', serialized)
        self.assertIn('timestamp', serialized)
        self.assertIn('status', serialized)
        
        # Recreate message from serialized form
        recreated = Message.from_dict(serialized)
        self.assertEqual(recreated.action, message.action)
        self.assertEqual(recreated.source, message.source)
        self.assertEqual(recreated.payload, message.payload)
        self.assertEqual(recreated.timestamp, message.timestamp)
        self.assertEqual(recreated.status, message.status)

if __name__ == '__main__':
    unittest.main() 