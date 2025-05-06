import unittest
import time
import logging
import os
import sys
from datetime import datetime
import threading
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import only the necessary modules for message queue testing
from src.message_format import Message, create_response_message

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Mock dependencies
class MockMessage:
    def __init__(self, message_id, source, action, payload, timestamp=None):
        self.message_id = message_id
        self.source = source
        self.action = action
        self.payload = payload
        self.timestamp = timestamp or (datetime.now().timestamp() * 1000)
        self.status = None
        self.in_response_to = None
    
    def to_dict(self):
        return {
            'message_id': self.message_id,
            'source': self.source,
            'action': self.action,
            'payload': self.payload,
            'timestamp': self.timestamp
        }
    
    @staticmethod
    def from_dict(data):
        msg = MockMessage(
            data.get('message_id', ''),
            data.get('source', ''),
            data.get('action', ''),
            data.get('payload', {})
        )
        msg.timestamp = data.get('timestamp', 0)
        return msg
    
    @staticmethod
    def create(source, action, payload):
        from uuid import uuid4
        return MockMessage(
            str(uuid4()),
            source,
            action,
            payload
        )

class MockState:
    def __init__(self):
        self.ideas = []
        self.central = None
        self.next_id = 0
    
    def get_ideas(self):
        return self.ideas
    
    def set_ideas(self, ideas):
        self.ideas = ideas
    
    def get_central(self):
        return self.central
    
    def set_central(self, node_id):
        self.central = node_id

class MessageQueueTester:
    """A simpler version of the message queue for testing."""
    
    def __init__(self):
        self.queue = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._callback = None
        
    def start(self, callback):
        """Start the message queue worker thread."""
        self._callback = callback
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop)
        self._worker_thread.daemon = True
        self._worker_thread.start()
        
    def stop(self):
        """Stop the message queue worker thread."""
        if self._worker_thread:
            self._stop_event.set()
            self._worker_thread.join()
            self._worker_thread = None
        
    def enqueue(self, message):
        """Add a message to the queue."""
        with self._lock:
            self.queue.append(message)
            
    def _worker_loop(self):
        """Main worker loop for processing messages."""
        while not self._stop_event.is_set():
            try:
                # Check if there are any messages
                with self._lock:
                    if self.queue:
                        message = self.queue.pop(0)
                        if self._callback:
                            self._callback(message)
            except Exception as e:
                logger.error(f"Error in message queue worker: {str(e)}")
            time.sleep(0.1)  # Prevent busy waiting

class TestMessageQueueWithoutDependencies(unittest.TestCase):
    """Test message queue without external dependencies."""
    
    def setUp(self):
        """Set up test case."""
        self.queue = MessageQueueTester()
        self.mock_state = MockState()
        
    def tearDown(self):
        """Clean up after test case."""
        self.queue.stop()
        
    def test_queue_initialization(self):
        """Test queue initialization."""
        self.assertIsNotNone(self.queue)
        self.assertEqual(len(self.queue.queue), 0)
        
    def test_message_enqueue(self):
        """Test enqueueing a message."""
        message = MockMessage.create('test', 'test_action', {'test': 'data'})
        self.queue.enqueue(message)
        
        with self.queue._lock:
            self.assertEqual(len(self.queue.queue), 1)
            
    def test_queue_callback(self):
        """Test that callback is called when message is processed."""
        # Track processed messages
        processed = []
        
        def test_callback(message):
            processed.append(message)
            
        # Start queue with test callback
        self.queue.start(test_callback)
        
        # Enqueue messages
        messages = [
            MockMessage.create('test', f'action_{i}', {'data': i})
            for i in range(3)
        ]
        
        for msg in messages:
            self.queue.enqueue(msg)
            
        # Wait for processing
        time.sleep(0.5)
        
        # Verify all messages were processed
        self.assertEqual(len(processed), 3)
        for i, msg in enumerate(processed):
            self.assertEqual(msg.action, f'action_{i}')
            
    def test_direct_message_processing(self):
        """Test direct message processing without queue."""
        # Define a simple message handler
        def handler(message):
            if message.action == 'test_action':
                return MockMessage.create(
                    'backend',
                    'test_response',
                    {'result': 'success', 'original_data': message.payload}
                )
            return None
            
        # Process a message directly
        message = MockMessage.create('test', 'test_action', {'test': 'data'})
        response = handler(message)
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertEqual(response.action, 'test_response')
        self.assertEqual(response.payload['result'], 'success')
        self.assertEqual(response.payload['original_data'], {'test': 'data'})
        
    def test_queue_processing_flow(self):
        """Test full message processing flow."""
        # Track processed messages and their responses
        processed = []
        responses = []
        
        def test_handler(message):
            processed.append(message)
            response = MockMessage.create(
                'backend',
                f'{message.action}_response',
                {'handled': True, 'original_action': message.action}
            )
            responses.append(response)
            return response
            
        # Start queue with test handler
        self.queue.start(test_handler)
        
        # Define test actions
        actions = ['create', 'update', 'delete', 'view']
        
        # Enqueue messages for each action
        for action in actions:
            message = MockMessage.create('frontend', action, {'action_type': action})
            self.queue.enqueue(message)
            
        # Wait for processing
        time.sleep(0.5)
        
        # Verify all messages were processed
        self.assertEqual(len(processed), len(actions))
        
        # Verify responses
        self.assertEqual(len(responses), len(actions))
        for i, action in enumerate(actions):
            self.assertEqual(responses[i].action, f'{action}_response')
            self.assertEqual(responses[i].payload['original_action'], action)

# Run the tests
if __name__ == '__main__':
    unittest.main() 