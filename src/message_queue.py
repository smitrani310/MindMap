"""
Message queue and retry mechanism for Enhanced Mind Map.
Handles message queuing, retries, and acknowledgment tracking.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

# Import necessary modules - use try/except to handle possible import errors
try:
    import streamlit as st
except ImportError:
    # Create a mock streamlit for environments without streamlit
    class MockStreamlit:
        def __init__(self):
            self.session_state = {}
        def rerun(self):
            pass
    st = MockStreamlit()

# Import state functions safely
try:
    from src.state import (
        get_ideas, set_ideas, get_central, set_central,
        get_next_id, increment_next_id, add_idea, save_data
    )
except ImportError:
    # Provide mock state functions if imports fail
    def get_ideas(): return st.session_state.get('ideas', [])
    def set_ideas(ideas): st.session_state['ideas'] = ideas
    def get_central(): return st.session_state.get('central')
    def set_central(node_id): st.session_state['central'] = node_id
    def get_next_id(): return st.session_state.get('next_id', 1)
    def increment_next_id():
        current = st.session_state.get('next_id', 1)
        st.session_state['next_id'] = current + 1
        return current + 1
    def add_idea(idea):
        ideas = st.session_state.get('ideas', [])
        ideas.append(idea)
        st.session_state['ideas'] = ideas
    def save_data(): pass

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
                return create_response_message(message, 'failed', f'Unknown action type: {message.action}')
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return create_response_message(message, 'failed', str(e))

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
                return create_response_message(message, 'completed', payload={
                    'selected_node': closest_node['id']
                })
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
                return create_response_message(message, 'completed', payload={
                    'edit_node': closest_node['id']
                })
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
                # Delete the node and all its descendants
                ideas = get_ideas()
                
                # Don't delete the central node
                if closest_node['id'] == get_central():
                    logger.warning(f"Cannot delete central node {closest_node['id']}")
                    return create_response_message(message, 'failed', 'Cannot delete central node')
                
                # Collect all descendants to delete
                to_delete = set()
                
                def collect_descendants(node_id):
                    to_delete.add(node_id)
                    for idea in ideas:
                        if idea.get('parent') == node_id:
                            collect_descendants(idea['id'])
                
                collect_descendants(closest_node['id'])
                
                # Remove the nodes
                ideas = [idea for idea in ideas if idea['id'] not in to_delete]
                set_ideas(ideas)
                save_data()
                
                # Trigger UI update
                st.rerun()
                
                return create_response_message(message, 'completed', payload={
                    'deleted_nodes': list(to_delete)
                })
            else:
                logger.warning(f"No node found near context menu coordinates")
                return create_response_message(message, 'failed', 'No node found near context menu coordinates')

        except Exception as e:
            logger.error(f"Error processing canvas context menu: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_new_node(self, message: Message) -> Message:
        """Handle new node creation."""
        try:
            # Extract node data
            node_data = message.payload
            
            # Generate a new node ID
            node_id = get_next_id()
            increment_next_id()
            
            # Create the node
            new_node = {
                'id': node_id,
                'label': node_data.get('label', 'New Node'),
                'description': node_data.get('description', ''),
                'urgency': node_data.get('urgency', 'medium'),
                'tag': node_data.get('tag', ''),
                'size': node_data.get('size', 20),
                'x': node_data.get('x', 0),
                'y': node_data.get('y', 0),
                'parent': node_data.get('parent', get_central())
            }
            
            # Add the node to the ideas
            add_idea(new_node)
            save_data()
            
            # Trigger UI update
            st.rerun()
            
            return create_response_message(message, 'completed', payload={
                'node_id': node_id,
                'node': new_node
            })
            
        except Exception as e:
            logger.error(f"Error creating new node: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_edit_node(self, message: Message) -> Message:
        """Handle node editing."""
        try:
            # Extract node data
            node_data = message.payload
            node_id = node_data.get('node_id')
            
            if node_id is None:
                return create_response_message(message, 'failed', 'No node ID provided')
            
            # Find the node
            ideas = get_ideas()
            node_index = next((i for i, idea in enumerate(ideas) if idea['id'] == node_id), None)
            
            if node_index is None:
                return create_response_message(message, 'failed', f'Node with ID {node_id} not found')
            
            # Update the node
            for key, value in node_data.items():
                if key != 'node_id' and key != 'id':
                    ideas[node_index][key] = value
            
            # Save the changes
            set_ideas(ideas)
            save_data()
            
            # Trigger UI update
            st.rerun()
            
            return create_response_message(message, 'completed', payload={
                'node_id': node_id,
                'node': ideas[node_index]
            })
            
        except Exception as e:
            logger.error(f"Error editing node: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_delete(self, message: Message) -> Message:
        """Handle node deletion."""
        try:
            # Extract node ID
            node_id = message.payload.get('node_id')
            
            if node_id is None:
                return create_response_message(message, 'failed', 'No node ID provided')
            
            # Get ideas
            ideas = get_ideas()
            
            # Don't delete the central node
            if node_id == get_central():
                logger.warning(f"Cannot delete central node {node_id}")
                return create_response_message(message, 'failed', 'Cannot delete central node')
            
            # Collect all descendants to delete
            to_delete = set()
            
            def collect_descendants(node_id):
                to_delete.add(node_id)
                for idea in ideas:
                    if idea.get('parent') == node_id:
                        collect_descendants(idea['id'])
            
            collect_descendants(node_id)
            
            # Remove the nodes
            ideas = [idea for idea in ideas if idea['id'] not in to_delete]
            set_ideas(ideas)
            save_data()
            
            # Trigger UI update
            st.rerun()
            
            return create_response_message(message, 'completed', payload={
                'deleted_nodes': list(to_delete)
            })
            
        except Exception as e:
            logger.error(f"Error deleting node: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_position(self, message: Message) -> Message:
        """Handle node position update."""
        try:
            # Extract node data
            node_id = message.payload.get('id')
            x = message.payload.get('x')
            y = message.payload.get('y')
            
            if node_id is None:
                return create_response_message(message, 'failed', 'No node ID provided')
            
            if x is None or y is None:
                return create_response_message(message, 'failed', 'No position coordinates provided')
            
            # Find the node
            ideas = get_ideas()
            node_index = next((i for i, idea in enumerate(ideas) if idea['id'] == node_id), None)
            
            if node_index is None:
                return create_response_message(message, 'failed', f'Node with ID {node_id} not found')
            
            # Update the position
            ideas[node_index]['x'] = x
            ideas[node_index]['y'] = y
            
            # Save the changes
            set_ideas(ideas)
            save_data()
            
            return create_response_message(message, 'completed', payload={
                'node_id': node_id,
                'x': x,
                'y': y
            })
            
        except Exception as e:
            logger.error(f"Error updating node position: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_reparent(self, message: Message) -> Message:
        """Handle node reparenting."""
        try:
            # Extract node data
            node_id = message.payload.get('node_id')
            new_parent_id = message.payload.get('parent_id')
            
            if node_id is None:
                return create_response_message(message, 'failed', 'No node ID provided')
            
            if new_parent_id is None:
                return create_response_message(message, 'failed', 'No parent ID provided')
            
            # Find the node
            ideas = get_ideas()
            node_index = next((i for i, idea in enumerate(ideas) if idea['id'] == node_id), None)
            
            if node_index is None:
                return create_response_message(message, 'failed', f'Node with ID {node_id} not found')
            
            # Check if the new parent exists
            if not any(idea['id'] == new_parent_id for idea in ideas):
                return create_response_message(message, 'failed', f'Parent node with ID {new_parent_id} not found')
            
            # Check for circular references
            def would_create_cycle(node_id, new_parent_id):
                # If we're trying to make a node its own parent
                if node_id == new_parent_id:
                    return True
                
                # Check if any ancestor of new_parent_id is node_id
                current = new_parent_id
                while current is not None:
                    if current == node_id:
                        return True
                    current_node = next((idea for idea in ideas if idea['id'] == current), None)
                    current = current_node.get('parent') if current_node else None
                
                return False
            
            if would_create_cycle(node_id, new_parent_id):
                return create_response_message(message, 'failed', 'Cannot reparent node: would create a cycle')
            
            # Update the parent
            ideas[node_index]['parent'] = new_parent_id
            
            # Save the changes
            set_ideas(ideas)
            save_data()
            
            # Trigger UI update
            st.rerun()
            
            return create_response_message(message, 'completed', payload={
                'node_id': node_id,
                'parent_id': new_parent_id
            })
            
        except Exception as e:
            logger.error(f"Error reparenting node: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_center_node(self, message: Message) -> Message:
        """Handle setting a node as the central focus."""
        try:
            # Extract node ID
            node_id = message.payload.get('id')
            
            if node_id is None:
                return create_response_message(message, 'failed', 'No node ID provided')
            
            # Make sure the node exists
            ideas = get_ideas()
            node = next((idea for idea in ideas if idea['id'] == node_id), None)
            
            if node is None:
                return create_response_message(message, 'failed', f'Node with ID {node_id} not found')
            
            # Set the central node
            set_central(node_id)
            save_data()
            
            # Trigger UI update
            st.rerun()
            
            return create_response_message(message, 'completed', payload={
                'central_node': node_id
            })
            
        except Exception as e:
            logger.error(f"Error centering node: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_select_node(self, message: Message) -> Message:
        """Handle node selection."""
        try:
            # Extract node ID
            node_id = message.payload.get('id')
            
            if node_id is None:
                return create_response_message(message, 'failed', 'No node ID provided')
            
            # Make sure the node exists
            ideas = get_ideas()
            node = next((idea for idea in ideas if idea['id'] == node_id), None)
            
            if node is None:
                return create_response_message(message, 'failed', f'Node with ID {node_id} not found')
            
            # Select the node
            st.session_state['selected_node'] = node_id
            
            # Trigger UI update
            st.rerun()
            
            return create_response_message(message, 'completed', payload={
                'selected_node': node_id
            })
            
        except Exception as e:
            logger.error(f"Error selecting node: {str(e)}")
            return create_response_message(message, 'failed', str(e))

    def _handle_undo(self, message: Message) -> Message:
        """Handle undo action."""
        # This is a placeholder for undo functionality
        # Implement history tracking and state restoration
        logger.warning("Undo functionality not yet implemented")
        return create_response_message(message, 'failed', 'Undo functionality not yet implemented')

    def _handle_redo(self, message: Message) -> Message:
        """Handle redo action."""
        # This is a placeholder for redo functionality
        # Implement history tracking and state restoration
        logger.warning("Redo functionality not yet implemented")
        return create_response_message(message, 'failed', 'Redo functionality not yet implemented')

# Create a singleton instance
message_queue = MessageQueue() 