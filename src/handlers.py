# Message/event handlers and error handling for MindMap
import streamlit as st
import logging
from src.state import get_ideas, get_central, set_central, get_next_id, increment_next_id, add_idea, set_ideas, get_store, save_data
from src.history import save_state_to_history, perform_undo, perform_redo
from src.utils import recalc_size, collect_descendants, find_node_by_id, find_closest_node, handle_error, validate_node_exists, validate_payload, extract_canvas_coordinates, standard_response
from src.message_format import Message, validate_message, create_response_message
from typing import Dict, Any, Optional, Callable, List, Tuple
import uuid
from datetime import datetime
from src.node_utils import update_node_position, update_node_position_service
from src.canvas_utils import handle_canvas_interaction
from src.position_utils import handle_position_message
import traceback

logger = logging.getLogger(__name__)

# Registry of message handlers
_message_handlers = {}

def register_handler(action: str, handler_func: Callable):
    """Register a message handler function for a specific action."""
    _message_handlers[action] = handler_func

def handle_exception(e):
    """Handle exceptions with proper logging and user feedback."""
    error_msg = f"An error occurred: {str(e)}"
    logger.error(error_msg)
    logger.error(f"Error details: {type(e).__name__}")
    st.error(error_msg)
    st.exception(e)

def is_circular(child_id, parent_id, nodes):
    """
    Check if making parent_id a parent of child_id would create a circular reference.
    Uses an optimized algorithm to detect cycles.
    """
    if child_id == parent_id:
        return True
        
    # Use a more efficient set-based approach for cycle detection
    visited = set()
    current_id = parent_id
    
    while current_id is not None:
        if current_id == child_id:
            return True
            
        if current_id in visited:
            return True
            
        visited.add(current_id)
        
        # Find the parent node
        parent_node = find_node_by_id(nodes, current_id)
        if not parent_node:
            return False
            
        current_id = parent_node.get('parent')
        
    return False

# Canvas-related handler functions
def handle_canvas_click(message: Message) -> Dict[str, Any]:
    """Handle canvas click events using the canvas utilities."""
    return handle_canvas_interaction(message, 'click')

def handle_canvas_dblclick(message: Message) -> Dict[str, Any]:
    """Handle canvas double-click events using the canvas utilities."""
    return handle_canvas_interaction(message, 'dblclick')

def handle_canvas_contextmenu(message: Message) -> Dict[str, Any]:
    """Handle canvas context menu events using the canvas utilities."""
    return handle_canvas_interaction(message, 'contextmenu')

def handle_undo(message: Message) -> Dict[str, Any]:
    """Handle undo requests."""
    if perform_undo():
        st.rerun()
    return standard_response(message, True)

def handle_redo(message: Message) -> Dict[str, Any]:
    """Handle redo requests."""
    if perform_redo():
        st.rerun()
    return standard_response(message, True)

def handle_position_update(message: Message) -> Dict[str, Any]:
    """Handle node position updates using position utilities."""
    try:
        # Use the centralized position handler
        result = handle_position_message(
            message=message,
            get_ideas_func=get_ideas,
            set_ideas_func=set_ideas,
            save_state_func=save_state_to_history,
            save_data_func=save_data,
            get_store_func=get_store
        )
        
        # Return standard response based on the result
        if result['success']:
            logger.info(f"Position update success: {result['message']}")
            return standard_response(message, True)
        else:
            logger.warning(f"Position update failed: {result['message']}")
            return standard_response(message, False, result['message'])
            
    except Exception as e:
        error_msg = handle_error(e, logger, "Error processing position update")
        return standard_response(message, False, error_msg)

def handle_edit_modal(message: Message) -> Dict[str, Any]:
    """Handle edit modal requests."""
    try:
        ideas = get_ideas()
        
        # Validate payload
        is_valid, error_msg, validated_payload = validate_payload(
            message.payload,
            required_fields=['id'],
            field_types={'id': int}
        )
        
        if not is_valid:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
            
        node_id = validated_payload['id']
        
        # Validate node exists
        success, node, error_msg = validate_node_exists(node_id, ideas, 'edit modal')
        if success:
            st.session_state['edit_node'] = node_id
            st.rerun()
            return standard_response(message, True)
        else:
            logger.warning(error_msg)
            return standard_response(message, False, 'Node not found')
            
    except Exception as e:
        error_msg = handle_error(e, logger, "Invalid edit modal request")
        return standard_response(message, False, error_msg)

def handle_select_node(message: Message) -> Dict[str, Any]:
    """Handle node selection requests."""
    try:
        ideas = get_ideas()
        
        # Validate payload
        is_valid, error_msg, validated_payload = validate_payload(
            message.payload,
            required_fields=['id'],
            field_types={'id': int}
        )
        
        if not is_valid:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
        
        node_id = validated_payload['id']
        logger.info(f"Processing select_node action for node ID: {node_id}")
        
        # Use the validation utility
        success, node, error_msg = validate_node_exists(node_id, ideas, 'select')
        if success:
            logger.info(f"Node {node_id} found, setting as selected node")
            st.session_state['selected_node'] = node_id
            st.rerun()
            return standard_response(message, True)
        else:
            logger.warning(error_msg)
            return standard_response(message, False, 'Node not found')
    except Exception as e:
        error_msg = handle_error(e, logger, "Error processing select node request")
        return standard_response(message, False, error_msg)

def handle_center_node(message: Message) -> Dict[str, Any]:
    """Handle node centering requests."""
    try:
        ideas = get_ideas()
        
        # Validate payload
        is_valid, error_msg, validated_payload = validate_payload(
            message.payload,
            required_fields=['id'],
            field_types={'id': int}
        )
        
        if not is_valid:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
        
        node_id = validated_payload['id']
        
        # Use the validation utility
        success, node, error_msg = validate_node_exists(node_id, ideas, 'center')
        if success:
            set_central(node_id)
            st.rerun()
            return standard_response(message, True)
        else:
            logger.warning(error_msg)
            return standard_response(message, False, 'Node not found')
    except Exception as e:
        error_msg = handle_error(e, logger, "Error processing center node request")
        return standard_response(message, False, error_msg)

def handle_delete_node(message: Message) -> Dict[str, Any]:
    """Handle node deletion requests."""
    try:
        ideas = get_ideas()
        save_state_to_history()
        
        # Handle both 'id' and 'node_id' in payload for compatibility
        # Validate payload
        is_valid, error_msg, validated_payload = validate_payload(
            message.payload,
            field_types={'id': int, 'node_id': int}
        )
        
        if not is_valid:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
            
        # Use either id or node_id
        node_id = validated_payload.get('id', validated_payload.get('node_id'))
        if node_id is None:
            return standard_response(message, False, "Missing node id")
        
        # Use the validation utility
        success, node, error_msg = validate_node_exists(node_id, ideas, 'delete')
        if not success:
            logger.warning(error_msg)
            return standard_response(message, False, 'Node not found')
            
        # Use the utility function to collect descendants
        to_remove = collect_descendants(node_id, ideas)
        
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
        return standard_response(message, True)
    except Exception as e:
        error_msg = handle_error(e, logger, "Invalid delete request")
        return standard_response(message, False, error_msg)

def handle_reparent_node(message: Message) -> Dict[str, Any]:
    """Handle node reparenting requests."""
    try:
        ideas = get_ideas()
        save_state_to_history()
        
        # Validate payload
        is_valid, error_msg, validated_payload = validate_payload(
            message.payload,
            required_fields=['id', 'parent'],
            field_types={'id': int, 'parent': int}
        )
        
        if not is_valid:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
            
        child_id = validated_payload['id']
        parent_id = validated_payload['parent']
        
        # Validate that both nodes exist
        child_success, child, child_error = validate_node_exists(child_id, ideas, 'reparent child')
        if not child_success:
            logger.warning(child_error)
            return standard_response(message, False, 'Child node not found')
        
        parent_success, parent, parent_error = validate_node_exists(parent_id, ideas, 'reparent parent')
        if not parent_success:
            logger.warning(parent_error)
            return standard_response(message, False, 'Parent node not found')
        
        if is_circular(child_id, parent_id, ideas):
            logger.warning(f"Circular reference detected: {child_id} -> {parent_id}")
            return standard_response(message, False, 'Cannot create circular parent-child relationships')
            
        child['parent'] = parent_id
        if not child.get('edge_type'):
            child['edge_type'] = 'default'
        
        # Save changes to data file
        logger.debug(f"Saving after reparenting node {child_id} to parent {parent_id}")
        set_ideas(ideas)
        save_data(get_store())
            
        st.rerun()
        return standard_response(message, True)
    except Exception as e:
        error_msg = handle_error(e, logger, "Invalid reparent request")
        return standard_response(message, False, error_msg)

def handle_new_node(message: Message) -> Dict[str, Any]:
    """Handle new node creation requests."""
    try:
        save_state_to_history()
        central = get_central()
        
        # Validate payload
        is_valid, error_msg, validated_payload = validate_payload(
            message.payload,
            field_types={
                'label': str,
                'title': str,
                'description': str,
                'urgency': str,
                'tag': str,
                'x': float,
                'y': float
            }
        )
        
        if not is_valid:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
            
        # Map the payload fields for compatibility
        label = validated_payload.get('label', validated_payload.get('title', ''))
        description = validated_payload.get('description', '')
        
        # Validate label
        if not label:
            logger.warning("New node request with empty label")
            return standard_response(message, False, 'New node request with empty label')
            
        new_node = {
            'id': get_next_id(),
            'label': label.strip(),
            'description': description,
            'urgency': validated_payload.get('urgency', 'medium'),
            'tag': validated_payload.get('tag', ''),
            'parent': central,
            'edge_type': 'default' if central is not None else None,
            'x': validated_payload.get('x'),
            'y': validated_payload.get('y')
        }
        recalc_size(new_node)
        add_idea(new_node)
        increment_next_id()
        
        # Save changes to data file
        logger.debug(f"Saving after creating new node with ID {new_node['id']}")
        save_data(get_store())
        
        st.rerun()
        return standard_response(message, True, None, {'node_id': new_node['id']})
    except Exception as e:
        error_msg = handle_error(e, logger, "Invalid new node request")
        return standard_response(message, False, error_msg)

def handle_edit_node(message: Message) -> Dict[str, Any]:
    """Handle node editing requests."""
    try:
        ideas = get_ideas()
        save_state_to_history()
        
        # Validate the payload
        is_valid, error_msg, validated_payload = validate_payload(
            message.payload,
            required_fields=['id'] if 'id' in message.payload else ['node_id'],
            field_types={
                'id': int, 
                'node_id': int,
                'label': str,
                'title': str,
                'description': str,
                'urgency': str,
                'tag': str,
                'x': float,
                'y': float
            }
        )
        
        if not is_valid:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
        
        # Handle both 'node_id' and 'id' in payload for compatibility
        node_id = validated_payload.get('node_id', validated_payload.get('id'))
        
        # Use the validation utility
        success, node, error_msg = validate_node_exists(node_id, ideas, 'edit')
        if not success:
            logger.warning(error_msg)
            return standard_response(message, False, 'Node not found')

        # Update node properties with field name compatibility
        if 'label' in validated_payload or 'title' in validated_payload:
            node['label'] = validated_payload.get('label', validated_payload.get('title')).strip()
        if 'description' in validated_payload:
            node['description'] = validated_payload['description']
        if 'urgency' in validated_payload:
            node['urgency'] = validated_payload['urgency']
        if 'tag' in validated_payload:
            node['tag'] = validated_payload['tag']
        if 'x' in validated_payload:
            node['x'] = validated_payload['x']
        if 'y' in validated_payload:
            node['y'] = validated_payload['y']

        recalc_size(node)
        set_ideas(ideas)
        save_data(get_store())

        st.rerun()
        return standard_response(message, True)
    except Exception as e:
        error_msg = handle_error(e, logger, "Error processing edit node request")
        return standard_response(message, False, error_msg)

def handle_message(msg_data: Dict[str, Any]) -> Optional[Message]:
    """Handle messages from the client using standardized message format."""
    try:
        # Validate message format
        if not validate_message(msg_data):
            logger.error(f"Invalid message format: {msg_data}")
            return create_response_message(
                Message(
                    message_id=str(uuid.uuid4()),
                    source='backend',
                    action=f"{msg_data.get('action', 'unknown')}_response",
                    payload={},
                    timestamp=datetime.now().timestamp() * 1000
                ),
                'failed',
                'Invalid message format'
            )

        # Convert to Message object
        message = Message.from_dict(msg_data)
        logger.info(f"Processing message: {message.action} (ID: {message.message_id})")
            
        # Check if we have a registered handler for this action
        action = message.action
        
        # Map deprecated action names to standardized ones
        if action == 'delete':
            action = 'delete_node'
        elif action == 'create_node':
            action = 'new_node'
        
        if action in _message_handlers:
            return _message_handlers[action](message)
        else:
            logger.warning(f"No handler registered for action: {action}")
            return standard_response(message, False, f"Unknown action type: {action}")
            
    except Exception as e:
        error_msg = handle_error(e, logger, "Error processing message")
        return create_response_message(
            Message(
                message_id=str(uuid.uuid4()),
                source='backend',
                action=f"{msg_data.get('action', 'unknown')}_response",
                payload={},
                timestamp=datetime.now().timestamp() * 1000
            ),
            'failed',
            error_msg
        )

# Register all handlers
register_handler('canvas_click', handle_canvas_click)
register_handler('canvas_dblclick', handle_canvas_dblclick)
register_handler('canvas_contextmenu', handle_canvas_contextmenu)
register_handler('undo', handle_undo)
register_handler('redo', handle_redo)
register_handler('pos', handle_position_update)
register_handler('edit_modal', handle_edit_modal)
register_handler('select_node', handle_select_node)
register_handler('center_node', handle_center_node)
register_handler('delete_node', handle_delete_node)
register_handler('reparent', handle_reparent_node)
register_handler('new_node', handle_new_node)
register_handler('edit_node', handle_edit_node) 