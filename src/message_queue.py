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
        self.queue = []
        self.processing = False
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
            self.queue.append(message)
            logger.debug(f"Message {message.message_id} enqueued")
            
    def acknowledge(self, message_id: str) -> None:
        """Acknowledge successful processing of a message."""
        with self._lock:
            if message_id in self.processing:
                del self.processing[message_id]
                logger.debug(f"Message {message_id} acknowledged")
            else:
                logger.warning(f"Received acknowledgment for unknown message {message_id}")
                
    def retry(self, message_id: str) -> None:
        """Handle retry for a failed message."""
        with self._lock:
            if message_id not in self.processing:
                logger.warning(f"Received retry request for unknown message {message_id}")
                return
                
            queued = self.processing[message_id]
            queued.retry_count += 1
            queued.last_retry_time = time.time()
            
            if queued.retry_count >= queued.max_retries:
                logger.error(f"Message {message_id} exceeded max retries")
                del self.processing[message_id]
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
                self.queue.append(new_queued)
                del self.processing[message_id]
                logger.info(f"Message {message_id} queued for retry {queued.retry_count}")
                
    def _worker_loop(self):
        """Main worker loop for processing messages."""
        while not self._stop_event.is_set():
            try:
                # Check if there are any messages in the queue
                with self._lock:
                    if self.queue:
                        message = self.queue.pop(0)
                        # Process the message with the correct method call
                        response = self._process_next_message(message)
                        # Handle response if needed
                        if response and self._callback:
                            self._callback(response)
            except Exception as e:
                logger.error(f"Error in message queue worker: {str(e)}")
            time.sleep(0.1)  # Prevent busy waiting
            
    def _process_next_message(self, message: Message) -> Optional[Message]:
        """Process a single message and return the response."""
        try:
            # Handle different action types
            if message.action == 'canvas_click':
                return self._handle_canvas_click(message)
            elif message.action == 'canvas_dblclick':
                return self._handle_canvas_dblclick(message)
            elif message.action == 'canvas_contextmenu':
                return self._handle_canvas_contextmenu(message)
            elif message.action == 'new_node' or message.action == 'create_node':
                return self._handle_new_node(message)
            elif message.action == 'edit_node':
                return self._handle_edit_node(message)
            elif message.action == 'delete' or message.action == 'delete_node':
                return self._handle_delete(message)
            elif message.action == 'pos':
                return self._handle_position(message)
            elif message.action == 'reparent':
                return self._handle_reparent(message)
            elif message.action == 'center_node':
                return self._handle_center_node(message)
            elif message.action == 'select_node':
                return self._handle_select_node(message)
            elif message.action == 'undo':
                return self._handle_undo(message)
            elif message.action == 'redo':
                return self._handle_redo(message)
            else:
                return create_response_message(message, 'failed', 'Unknown action type')
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def process_queue(self) -> None:
        """Process all messages in the queue."""
        if self.processing:
            return

        self.processing = True
        try:
            while self.queue:
                message = self.queue.pop(0)
                response = self._process_next_message(message)
                if response:
                    # Handle response (e.g., send back to frontend)
                    pass
        finally:
            self.processing = False

    def _handle_canvas_click(self, message: Message) -> Message:
        """Handle canvas click event."""
        try:
            # Extract click coordinates
            click_x = message.payload.get('x', 0)
            click_y = message.payload.get('y', 0)
            canvas_width = message.payload.get('canvasWidth', 800)
            canvas_height = message.payload.get('canvasHeight', 600)

            # Find the nearest node
            closest_node = None
            min_distance = float('inf')

            for node in get_ideas():
                if node.get('x') is not None and node.get('y') is not None:
                    # Scale coordinates to match canvas
                    node_x = (node['x'] + canvas_width/2)
                    node_y = (node['y'] + canvas_height/2)

                    # Calculate distance
                    distance = ((node_x - click_x) ** 2 + (node_y - click_y) ** 2) ** 0.5

                    if distance < min_distance:
                        min_distance = distance
                        closest_node = node

            # Use a threshold based on canvas dimensions
            click_threshold = min(canvas_width, canvas_height) * 0.08

            if closest_node and min_distance <= click_threshold:
                # Select the node
                st.session_state['selected_node'] = closest_node['id']
                st.rerun()
                return create_response_message(message, 'completed')
            else:
                logger.warning(f"No node found near click coordinates (closest: {closest_node['label'] if closest_node else 'None'} at distance: {min_distance:.2f}, threshold: {click_threshold:.2f})")
                return create_response_message(message, 'failed', 'No node found near click coordinates')

        except Exception as e:
            logger.error(f"Error processing canvas click: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_canvas_dblclick(self, message: Message) -> Message:
        """Handle canvas double-click event."""
        try:
            # Extract click coordinates
            click_x = message.payload.get('x', 0)
            click_y = message.payload.get('y', 0)
            canvas_width = message.payload.get('canvasWidth', 800)
            canvas_height = message.payload.get('canvasHeight', 600)

            # Find the nearest node
            closest_node = None
            min_distance = float('inf')

            for node in get_ideas():
                if node.get('x') is not None and node.get('y') is not None:
                    # Scale coordinates to match canvas
                    node_x = (node['x'] + canvas_width/2)
                    node_y = (node['y'] + canvas_height/2)

                    # Calculate distance
                    distance = ((node_x - click_x) ** 2 + (node_y - click_y) ** 2) ** 0.5

                    if distance < min_distance:
                        min_distance = distance
                        closest_node = node

            # Use a threshold based on canvas dimensions
            click_threshold = min(canvas_width, canvas_height) * 0.08

            if closest_node and min_distance <= click_threshold:
                # Open edit modal for the node
                st.session_state['edit_node'] = closest_node['id']
                st.rerun()
                return create_response_message(message, 'completed')
            else:
                logger.warning(f"No node found near double-click coordinates")
                return create_response_message(message, 'failed', 'No node found near double-click coordinates')

        except Exception as e:
            logger.error(f"Error processing canvas double-click: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_canvas_contextmenu(self, message: Message) -> Message:
        """Handle canvas context menu event."""
        try:
            # Extract click coordinates
            click_x = message.payload.get('x', 0)
            click_y = message.payload.get('y', 0)
            canvas_width = message.payload.get('canvasWidth', 800)
            canvas_height = message.payload.get('canvasHeight', 600)

            # Find the nearest node
            closest_node = None
            min_distance = float('inf')

            for node in get_ideas():
                if node.get('x') is not None and node.get('y') is not None:
                    # Scale coordinates to match canvas
                    node_x = (node['x'] + canvas_width/2)
                    node_y = (node['y'] + canvas_height/2)

                    # Calculate distance
                    distance = ((node_x - click_x) ** 2 + (node_y - click_y) ** 2) ** 0.5

                    if distance < min_distance:
                        min_distance = distance
                        closest_node = node

            # Use a threshold based on canvas dimensions
            click_threshold = min(canvas_width, canvas_height) * 0.08

            if closest_node and min_distance <= click_threshold:
                # Delete the node
                save_state_to_history()
                ideas = get_ideas()
                ideas.remove(closest_node)
                set_ideas(ideas)
                save_data(get_store())
                st.rerun()
                return create_response_message(message, 'completed')
            else:
                logger.warning(f"No node found near context menu coordinates")
                return create_response_message(message, 'failed', 'No node found near context menu coordinates')

        except Exception as e:
            logger.error(f"Error processing canvas context menu: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_new_node(self, message: Message) -> Message:
        """Handle new node creation."""
        try:
            save_state_to_history()
            central = get_central()

            # Validate label
            if not message.payload.get('label'):
                logger.warning("New node request with empty label")
                return create_response_message(message, 'failed', 'New node request with empty label')

            new_node = {
                'id': get_next_id(),
                'label': message.payload['label'].strip(),
                'description': message.payload.get('description', ''),
                'urgency': message.payload.get('urgency', 'medium'),
                'tag': message.payload.get('tag', ''),
                'parent': central,
                'edge_type': 'default' if central is not None else None,
                'x': message.payload.get('x'),
                'y': message.payload.get('y')
            }
            recalc_size(new_node)
            add_idea(new_node)
            increment_next_id()

            # Save changes to data file
            logger.debug(f"Saving after creating new node with ID {new_node['id']}")
            save_data(get_store())

            st.rerun()
            return create_response_message(message, 'completed', {'node_id': new_node['id']})

        except (KeyError, ValueError) as e:
            logger.error(f"Invalid new node request: {message.payload}")
            return create_response_message(message, 'failed', str(e))

    def _handle_edit_node(self, message: Message) -> Message:
        """Handle node editing."""
        try:
            save_state_to_history()
            node_id = int(message.payload['node_id'])
            ideas = get_ideas()
            node = next((n for n in ideas if n['id'] == node_id), None)

            if not node:
                logger.warning(f"Edit request for nonexistent node: {node_id}")
                return create_response_message(message, 'failed', 'Node not found')

            # Update node properties
            if 'label' in message.payload:
                node['label'] = message.payload['label'].strip()
            if 'description' in message.payload:
                node['description'] = message.payload['description']
            if 'urgency' in message.payload:
                node['urgency'] = message.payload['urgency']
            if 'tag' in message.payload:
                node['tag'] = message.payload['tag']
            if 'x' in message.payload:
                node['x'] = message.payload['x']
            if 'y' in message.payload:
                node['y'] = message.payload['y']

            recalc_size(node)
            set_ideas(ideas)
            save_data(get_store())

            st.rerun()
            return create_response_message(message, 'completed')

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid edit request: {message.payload}")
            return create_response_message(message, 'failed', str(e))

    def _handle_delete(self, message: Message) -> Message:
        """Handle node deletion."""
        try:
            save_state_to_history()
            node_id = int(message.payload['id'])
            ideas = get_ideas()

            if node_id not in {n['id'] for n in ideas}:
                logger.warning(f"Delete request for nonexistent node: {node_id}")
                return create_response_message(message, 'failed', 'Node not found')

            to_remove = set()
            def collect_descendants(node_id):
                to_remove.add(node_id)
                children = [n['id'] for n in ideas if n.get('parent') == node_id]
                for child_id in children:
                    if child_id not in to_remove:  # Avoid redundant processing
                        collect_descendants(child_id)

            collect_descendants(node_id)
            set_ideas([n for n in ideas if n['id'] not in to_remove])

            if get_central() in to_remove:
                set_central(None)

            # Also clear selected node if it was deleted
            if 'selected_node' in st.session_state and st.session_state['selected_node'] in to_remove:
                st.session_state['selected_node'] = None

            # Save changes to data file
            logger.debug(f"Saving after deleting node {node_id} and {len(to_remove)-1} descendants")
            save_data(get_store())

            st.rerun()
            return create_response_message(message, 'completed')

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid delete request: {message.payload}")
            return create_response_message(message, 'failed', str(e))

    def _handle_position(self, message: Message) -> Message:
        """Handle node position updates."""
        try:
            save_state_to_history()
            position_updated = False
            ideas = get_ideas()

            for k, v in message.payload.items():
                try:
                    node_id = int(k)
                    node = next((n for n in ideas if n['id'] == node_id), None)
                    if node:
                        # Validate position data
                        if isinstance(v, dict) and 'x' in v and 'y' in v:
                            node['x'], node['y'] = v['x'], v['y']
                            position_updated = True
                        else:
                            logger.warning(f"Invalid position data: {v}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid node ID or position: {k} -> {v}")
                    st.error(f"Invalid node ID: {k}")

            # Save position changes to data file
            if position_updated:
                logger.debug("Saving node position changes")
                set_ideas(ideas)
                save_data(get_store())

            return create_response_message(message, 'completed')

        except Exception as e:
            logger.error(f"Error processing position update: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_reparent(self, message: Message) -> Message:
        """Handle node reparenting."""
        try:
            save_state_to_history()
            child_id = int(message.payload['id'])
            parent_id = int(message.payload['parent'])
            ideas = get_ideas()

            # Validate that both nodes exist
            if child_id not in {n['id'] for n in ideas}:
                logger.warning(f"Reparent request for nonexistent child: {child_id}")
                return create_response_message(message, 'failed', 'Child node not found')

            if parent_id not in {n['id'] for n in ideas}:
                logger.warning(f"Reparent request for nonexistent parent: {parent_id}")
                return create_response_message(message, 'failed', 'Parent node not found')

            child = next((n for n in ideas if n['id'] == child_id), None)

            if is_circular(child_id, parent_id, ideas):
                logger.warning(f"Circular reference detected: {child_id} -> {parent_id}")
                return create_response_message(message, 'failed', 'Cannot create circular parent-child relationships')

            child['parent'] = parent_id
            if not child.get('edge_type'):
                child['edge_type'] = 'default'

            # Save changes to data file
            logger.debug(f"Saving after reparenting node {child_id} to parent {parent_id}")
            set_ideas(ideas)
            save_data(get_store())

            st.rerun()
            return create_response_message(message, 'completed')

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid reparent request: {message.payload}")
            return create_response_message(message, 'failed', str(e))

    def _handle_center_node(self, message: Message) -> Message:
        """Handle setting central node."""
        try:
            node_id = int(message.payload['id'])
            ideas = get_ideas()

            if node_id not in {n['id'] for n in ideas}:
                logger.warning(f"Center request for nonexistent node: {node_id}")
                return create_response_message(message, 'failed', 'Node not found')

            set_central(node_id)
            st.rerun()
            return create_response_message(message, 'completed')

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid center node request: {message.payload}")
            return create_response_message(message, 'failed', str(e))

    def _handle_select_node(self, message: Message) -> Message:
        """Handle node selection."""
        try:
            node_id = int(message.payload['id'])
            ideas = get_ideas()

            if node_id not in {n['id'] for n in ideas}:
                logger.warning(f"Select request for nonexistent node: {node_id}")
                return create_response_message(message, 'failed', 'Node not found')

            st.session_state['selected_node'] = node_id
            st.rerun()
            return create_response_message(message, 'completed')

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid select node request: {message.payload}")
            return create_response_message(message, 'failed', str(e))

    def _handle_undo(self, message: Message) -> Message:
        """Handle undo operation."""
        try:
            if perform_undo():
                st.rerun()
            return create_response_message(message, 'completed')
        except Exception as e:
            logger.error(f"Error performing undo: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_redo(self, message: Message) -> Message:
        """Handle redo operation."""
        try:
            if perform_redo():
                st.rerun()
            return create_response_message(message, 'completed')
        except Exception as e:
            logger.error(f"Error performing redo: {str(e)}")
            return create_response_message(message, 'failed', str(e))

# Global message queue instance
message_queue = MessageQueue() 