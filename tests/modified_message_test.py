import unittest
import time
import logging
import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import message format
from src.message_format import Message, create_response_message, validate_message

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class TestMessageFormat(unittest.TestCase):
    """Test message format and response creation."""
    
    def test_message_validation(self):
        """Test message validation functionality."""
        # Test valid message
        valid_message = {
            'message_id': '12345',
            'source': 'frontend',
            'action': 'canvas_click',
            'payload': {'x': 100, 'y': 100},
            'timestamp': 1617293033123
        }
        self.assertTrue(validate_message(valid_message))
        
        # Test invalid messages
        # Missing required fields
        invalid_message1 = {
            'action': 'canvas_click',
            'payload': {'x': 100, 'y': 100}
        }
        self.assertFalse(validate_message(invalid_message1))
        
        # Invalid action
        invalid_message2 = {
            'message_id': '12345',
            'source': 'frontend',
            'action': 'invalid_action',
            'payload': {},
            'timestamp': 1617293033123
        }
        self.assertFalse(validate_message(invalid_message2))
        
        # Invalid payload type
        invalid_message3 = {
            'message_id': '12345',
            'source': 'frontend',
            'action': 'canvas_click',
            'payload': 'not_a_dict',
            'timestamp': 1617293033123
        }
        self.assertFalse(validate_message(invalid_message3))
        
    def test_message_creation(self):
        """Test message creation."""
        # Create a message
        message = Message.create('frontend', 'canvas_click', {'x': 100, 'y': 100})
        
        # Verify message properties
        self.assertEqual(message.source, 'frontend')
        self.assertEqual(message.action, 'canvas_click')
        self.assertEqual(message.payload, {'x': 100, 'y': 100})
        self.assertIsNotNone(message.message_id)
        self.assertIsNotNone(message.timestamp)
        
        # Verify to_dict and from_dict
        message_dict = message.to_dict()
        message2 = Message.from_dict(message_dict)
        self.assertEqual(message.message_id, message2.message_id)
        self.assertEqual(message.action, message2.action)
        
    def test_response_message_creation(self):
        """Test response message creation."""
        # Create a message
        original_message = Message.create('frontend', 'canvas_click', {'x': 100, 'y': 100})
        
        # Create a response message - payload should be the 4th parameter, not 3rd
        response = create_response_message(original_message, 'completed', None, {'result': 'success'})
        
        # Verify response properties
        self.assertEqual(response.source, 'backend')
        self.assertEqual(response.action, 'canvas_click_response')
        self.assertEqual(response.status, 'completed')
        self.assertEqual(response.payload['result'], 'success')

if __name__ == '__main__':
    unittest.main() 