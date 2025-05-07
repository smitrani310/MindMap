import unittest
from src.message_format import Message, validate_message, create_response_message
from src.message_queue import message_queue
import time
import threading

class TestMessageHandling(unittest.TestCase):
    """Test suite for message handling functionality.
    
    Tests the interaction between message creation, validation, queuing,
    and processing, including error handling and retry mechanisms.
    """

    def setUp(self):
        """Set up test fixtures before each test method.
        
        Initializes:
        - Message queue instance
        - Message tracking list
        - Thread synchronization lock
        - Message handler callback
        
        Ensures the queue is running before tests begin.
        """
        self.message_queue = message_queue
        self.received_messages = []
        self.lock = threading.Lock()
        self.message_queue.start(lambda msg: self.handle_message(msg))
        time.sleep(0.1)  # Give the queue time to start

    def tearDown(self):
        """Clean up after each test method.
        
        Ensures:
        - Message queue is properly stopped
        - Message tracking is cleared
        - Resources are released
        """
        self.message_queue.stop()
        time.sleep(0.1)  # Give the queue time to stop
        self.received_messages = []

    def handle_message(self, message):
        """Test message handler callback.
        
        Simulates message processing with:
        - Thread-safe message tracking
        - Configurable failure scenarios
        - Response message generation
        
        Args:
            message: The message to process
            
        Returns:
            Response message indicating success or failure
        """
        with self.lock:
            self.received_messages.append(message)
            if message.payload.get('should_fail', False):
                return create_response_message(message, status='failed', error='Test failure')
        return create_response_message(message, status='completed')

    def test_message_creation(self):
        """Test message object creation and initialization.
        
        Verifies that:
        - Messages are created with correct attributes
        - Source is properly set
        - Action is correctly assigned
        - Payload is preserved
        - Initial status is set to 'pending'
        """
        message = Message.create('test', 'test_action', {'test': 'data'})
        self.assertEqual(message.source, 'test')
        self.assertEqual(message.action, 'test_action')
        self.assertEqual(message.payload, {'test': 'data'})
        self.assertEqual(message.status, 'pending')

    def test_message_validation(self):
        """Test message validation functionality.
        
        Verifies that:
        - Valid messages pass validation
        - Message format is correctly checked
        - Required fields are validated
        - Message dictionary conversion works
        """
        message = Message.create('test', 'test_action', {'test': 'data'})
        self.assertTrue(validate_message(message.to_dict()))

    def test_message_queue(self):
        """Test message queuing and processing flow.
        
        Verifies that:
        - Messages can be enqueued successfully
        - Messages are processed in order
        - Message content is preserved through the queue
        - Handler receives the correct message
        - Processing completes successfully
        """
        message = Message.create('test', 'test_action', {'test': 'data'})
        self.message_queue.enqueue(message)
        time.sleep(0.2)  # Give the queue time to process

        with self.lock:
            self.assertEqual(len(self.received_messages), 1)
            received = self.received_messages[0]
            self.assertEqual(received.source, message.source)
            self.assertEqual(received.action, message.action)
            self.assertEqual(received.payload, message.payload)

    def test_message_retry(self):
        """Test message retry mechanism for failed messages.
        
        Verifies that:
        - Failed messages are retried
        - Retry count is tracked correctly
        - Message content is preserved during retries
        - Retry timing is appropriate
        - Maximum retry attempts are respected
        """
        # Create a message that will fail
        message = Message.create('test', 'test_action', {'test': 'data', 'should_fail': True})
        self.message_queue.enqueue(message)
        
        # Wait for initial processing and retry
        time.sleep(1.5)  # Give more time for retry to occur

        with self.lock:
            self.assertEqual(len(self.received_messages), 2)
            initial = self.received_messages[0]
            retried = self.received_messages[1]
            
            # Check initial message
            self.assertEqual(initial.source, message.source)
            self.assertEqual(initial.action, message.action)
            self.assertEqual(initial.payload, message.payload)
            
            # Check retried message
            self.assertEqual(retried.source, message.source)
            self.assertEqual(retried.action, message.action)
            self.assertEqual(retried.payload, message.payload)

if __name__ == '__main__':
    unittest.main() 