"""
Message queue and retry mechanism for Enhanced Mind Map.
Handles message queuing, retries, and acknowledgment tracking.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from src.message_format import Message, create_response_message

logger = logging.getLogger(__name__)

@dataclass
class QueuedMessage:
    """Represents a message in the queue with retry information."""
    message: Message
    retry_count: int = 0
    max_retries: int = 3
    last_retry_time: float = 0
    retry_delay: float = 1.0  # seconds

class MessageQueue:
    """Handles message queuing and retry logic."""
    
    def __init__(self):
        self._queue: List[QueuedMessage] = []
        self._processing: Dict[str, QueuedMessage] = {}  # message_id -> QueuedMessage
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._callback: Optional[Callable[[Message], Message]] = None
        
    def start(self, callback: Callable[[Message], Message]):
        """Start the message queue worker thread."""
        if self._worker_thread is not None:
            logger.warning("Message queue worker thread already running")
            return
            
        self._callback = callback
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop)
        self._worker_thread.daemon = True
        self._worker_thread.start()
        logger.info("Message queue worker thread started")
        
    def stop(self):
        """Stop the message queue worker thread."""
        if self._worker_thread is None:
            return
            
        self._stop_event.set()
        self._worker_thread.join()
        self._worker_thread = None
        logger.info("Message queue worker thread stopped")
        
    def enqueue(self, message: Message) -> None:
        """Add a message to the queue."""
        with self._lock:
            queued = QueuedMessage(message=message)
            self._queue.append(queued)
            logger.debug(f"Message {message.message_id} enqueued")
            
    def acknowledge(self, message_id: str) -> None:
        """Acknowledge successful processing of a message."""
        with self._lock:
            if message_id in self._processing:
                del self._processing[message_id]
                logger.debug(f"Message {message_id} acknowledged")
            else:
                logger.warning(f"Received acknowledgment for unknown message {message_id}")
                
    def retry(self, message_id: str) -> None:
        """Handle retry for a failed message."""
        with self._lock:
            if message_id not in self._processing:
                logger.warning(f"Received retry request for unknown message {message_id}")
                return
                
            queued = self._processing[message_id]
            queued.retry_count += 1
            queued.last_retry_time = time.time()
            
            if queued.retry_count >= queued.max_retries:
                logger.error(f"Message {message_id} exceeded max retries")
                del self._processing[message_id]
            else:
                # Create a new message for retry with the same content
                new_message = Message.create(
                    source=queued.message.source,
                    action=queued.message.action,
                    payload=queued.message.payload
                )
                new_queued = QueuedMessage(
                    message=new_message,
                    retry_count=queued.retry_count,
                    last_retry_time=queued.last_retry_time
                )
                self._queue.append(new_queued)
                del self._processing[message_id]
                logger.info(f"Message {message_id} queued for retry {queued.retry_count}")
                
    def _worker_loop(self):
        """Main worker loop for processing messages."""
        while not self._stop_event.is_set():
            try:
                self._process_next_message()
            except Exception as e:
                logger.error(f"Error in message queue worker: {str(e)}")
            time.sleep(0.1)  # Prevent busy waiting
            
    def _process_next_message(self):
        """Process the next message in the queue."""
        with self._lock:
            if not self._queue:
                return
                
            # Get next message
            queued = self._queue.pop(0)
            current_time = time.time()
            
            # Check if we should wait before retrying
            if (queued.retry_count > 0 and 
                current_time - queued.last_retry_time < queued.retry_delay):
                self._queue.append(queued)
                return
                
            # Process message
            self._processing[queued.message.message_id] = queued
            
        # Release lock before calling callback
        if self._callback:
            try:
                response = self._callback(queued.message)
                if response and response.status == 'failed':
                    logger.error(f"Message {queued.message.message_id} processing failed: {response.error}")
                    self.retry(queued.message.message_id)
                else:
                    self.acknowledge(queued.message.message_id)
            except Exception as e:
                logger.error(f"Error processing message {queued.message.message_id}: {str(e)}")
                self.retry(queued.message.message_id)

# Global message queue instance
message_queue = MessageQueue() 