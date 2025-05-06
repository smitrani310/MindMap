import unittest
import time
import logging
import os
import sys
import threading
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SimpleQueueTest(unittest.TestCase):
    """Test the core threaded queue functionality."""
    
    def setUp(self):
        """Set up test case."""
        # Create a simple message queue with just the core functionality
        self.queue = SimpleQueue()
        
    def tearDown(self):
        """Clean up after test."""
        self.queue.stop()
        
    def test_queue_initialization(self):
        """Test queue initialization."""
        self.assertIsNotNone(self.queue)
        self.assertEqual(len(self.queue.queue), 0)
        self.assertFalse(self.queue._worker_thread is not None and self.queue._worker_thread.is_alive())
        
    def test_start_stop(self):
        """Test starting and stopping the queue."""
        # Define a simple callback
        def callback(message):
            return message
            
        # Start the queue
        self.queue.start(callback)
        
        # Verify queue is running
        self.assertTrue(self.queue._worker_thread is not None and self.queue._worker_thread.is_alive())
        
        # Stop the queue
        self.queue.stop()
        
        # Verify queue has stopped
        self.assertFalse(self.queue._worker_thread is not None and self.queue._worker_thread.is_alive())
        
    def test_enqueue_and_process(self):
        """Test enqueueing and processing messages."""
        # Keep track of processed messages
        processed_messages = []
        
        # Define callback
        def callback(message):
            processed_messages.append(message)
            return message
            
        # Start the queue
        self.queue.start(callback)
        
        # Enqueue some messages
        test_messages = [
            {"id": 1, "content": "Test 1"},
            {"id": 2, "content": "Test 2"},
            {"id": 3, "content": "Test 3"}
        ]
        
        for msg in test_messages:
            self.queue.enqueue(msg)
            
        # Wait for processing
        time.sleep(0.5)
        
        # Verify all messages were processed
        self.assertEqual(len(processed_messages), len(test_messages))
        
        # Verify message order was preserved
        for i, msg in enumerate(test_messages):
            self.assertEqual(processed_messages[i], msg)

class SimpleQueue:
    """A minimal message queue implementation for testing."""
    
    def __init__(self):
        """Initialize the queue."""
        self.queue = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._callback = None
        
    def start(self, callback):
        """Start the message queue worker thread."""
        if self._worker_thread is not None:
            return
            
        self._callback = callback
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop)
        self._worker_thread.daemon = True
        self._worker_thread.start()
        
    def stop(self):
        """Stop the message queue worker thread."""
        if self._worker_thread is None:
            return
            
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
                    if self.queue and self._callback:
                        message = self.queue.pop(0)
                        # Process the message (outside the lock)
                
                if 'message' in locals():
                    self._callback(message)
                    del message
                    
            except Exception as e:
                logger.error(f"Error in message queue worker: {str(e)}")
            time.sleep(0.1)  # Prevent busy waiting
            
if __name__ == '__main__':
    unittest.main() 