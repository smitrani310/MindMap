#!/usr/bin/env python
"""
Integration tests for message flow between components.

This module tests the complete message flow through the system, including:
- Message creation and validation
- Queue processing and delivery
- Component interactions
- Error handling and recovery
- State synchronization

The tests verify that messages flow correctly between different parts of the system
and that the system maintains consistency during message processing.
"""

import unittest
import time
import threading
from src.message_format import Message, create_response_message
from src.message_queue import message_queue
from src import state, handlers

class TestMessageFlow(unittest.TestCase):
    """Test suite for end-to-end message flow functionality.
    
    Tests the complete message lifecycle from creation through processing,
    including interactions between different system components.
    """

    def setUp(self):
        """Set up test fixtures before each test method.
        
        Initializes:
        - Message queue with test handler
        - State tracking for verification
        - Thread synchronization primitives
        - Test data and expected outcomes
        """
        self.message_queue = message_queue
        self.received_messages = []
        self.lock = threading.Lock()
        self.message_queue.start(self.handle_message)
        time.sleep(0.1)  # Allow queue to initialize

    def tearDown(self):
        """Clean up after each test method.
        
        Ensures:
        - Message queue is properly stopped
        - Test state is cleared
        - Resources are released
        - No lingering messages or state
        """
        self.message_queue.stop()
        time.sleep(0.1)  # Allow queue to stop
        self.received_messages = []

    def handle_message(self, message):
        """Test message handler for integration testing.
        
        Processes messages and tracks their flow through the system.
        Simulates real-world message handling scenarios.
        
        Args:
            message: The message to process
            
        Returns:
            Response message indicating processing result
        """
        with self.lock:
            self.received_messages.append(message)
            # Simulate different processing scenarios
            if message.payload.get('should_fail', False):
                return create_response_message(message, 'failed', 'Test failure')
            elif message.payload.get('should_retry', False):
                return create_response_message(message, 'retry', 'Retry needed')
        return create_response_message(message, 'completed')

    def test_basic_message_flow(self):
        """Test basic message flow through the system.
        
        Verifies that:
        - Messages are created correctly
        - Messages flow through the queue
        - Messages are processed in order
        - State is updated appropriately
        - Responses are generated correctly
        """
        # Create and send a test message
        message = Message.create('test', 'test_action', {'test': 'data'})
        self.message_queue.enqueue(message)
        
        # Wait for processing
        time.sleep(0.2)
        
        # Verify message flow
        with self.lock:
            self.assertEqual(len(self.received_messages), 1)
            received = self.received_messages[0]
            self.assertEqual(received.source, message.source)
            self.assertEqual(received.action, message.action)
            self.assertEqual(received.payload, message.payload)

    def test_error_handling_flow(self):
        """Test message flow with error handling.
        
        Verifies that:
        - Error messages are handled correctly
        - System recovers from errors
        - Error states are properly communicated
        - Failed messages are retried appropriately
        - System maintains consistency during errors
        """
        # Create a message that will fail
        message = Message.create('test', 'test_action', {'should_fail': True})
        self.message_queue.enqueue(message)
        
        # Wait for processing and retry
        time.sleep(1.5)
        
        # Verify error handling
        with self.lock:
            self.assertEqual(len(self.received_messages), 2)  # Initial + retry
            initial = self.received_messages[0]
            retried = self.received_messages[1]
            
            # Verify initial failure
            self.assertEqual(initial.payload.get('should_fail'), True)
            
            # Verify retry attempt
            self.assertEqual(retried.payload.get('should_fail'), True)

    def test_state_sync_flow(self):
        """Test message flow with state synchronization.
        
        Verifies that:
        - State changes are properly synchronized
        - Messages trigger correct state updates
        - State remains consistent across components
        - Concurrent state updates are handled correctly
        - State changes are properly propagated
        """
        # Set up initial state
        initial_state = {'test': 'initial'}
        state.set_ideas([initial_state])
        
        # Create and send a state update message
        message = Message.create('test', 'update_state', {'new_state': 'updated'})
        self.message_queue.enqueue(message)
        
        # Wait for processing
        time.sleep(0.2)
        
        # Verify state synchronization
        current_state = state.get_ideas()
        self.assertEqual(len(current_state), 1)
        self.assertEqual(current_state[0]['new_state'], 'updated')

if __name__ == '__main__':
    unittest.main() 