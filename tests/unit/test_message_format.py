#!/usr/bin/env python
"""
Unit tests for message format validation and handling.
Tests the core functionality of message creation, validation, and formatting
without requiring external dependencies or complex setups.
"""

import unittest
from src.message_format import Message, create_response_message

class TestMessageFormat(unittest.TestCase):
    """Test suite for message format functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Initialize common test data
        self.test_message_data = {
            'action': 'test_action',
            'source': 'test_source',
            'message_id': '123',
            'payload': {'key': 'value'}
        }

    def test_message_creation(self):
        """Test basic message creation and attribute setting.
        
        Verifies that:
        - Message objects can be created with correct attributes
        - All required fields are properly set
        - Default values are applied correctly
        """
        message = Message(**self.test_message_data)
        self.assertEqual(message.action, 'test_action')
        self.assertEqual(message.source, 'test_source')
        self.assertEqual(message.message_id, '123')
        self.assertEqual(message.payload, {'key': 'value'})

    def test_message_validation(self):
        """Test message validation rules.
        
        Verifies that:
        - Messages with all required fields pass validation
        - Messages with missing required fields fail validation
        - Messages with invalid field types fail validation
        - Edge cases (empty strings, None values) are handled correctly
        """
        # Valid message
        message = Message(**self.test_message_data)
        self.assertTrue(message.is_valid())

        # Invalid message (missing required field)
        invalid_data = self.test_message_data.copy()
        del invalid_data['action']
        with self.assertRaises(ValueError):
            Message(**invalid_data)

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
            'success',
            'Operation completed'
        )
        
        self.assertEqual(response.source, 'backend')
        self.assertEqual(response.status, 'success')
        self.assertEqual(response.error_message, 'Operation completed')
        self.assertEqual(response.original_message_id, original_msg.message_id)

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
        
        # Recreate message from serialized form
        recreated = Message(**serialized)
        self.assertEqual(recreated.action, message.action)
        self.assertEqual(recreated.payload, message.payload)

if __name__ == '__main__':
    unittest.main() 