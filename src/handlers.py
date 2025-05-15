"""
Message handlers for the Mind Map application.

This module contains handlers for different message types including:
- Node addition, updating, and deletion
- Canvas interactions
- Position updates
- Error handling
"""

from typing import Dict, Any, List, Callable, Optional, Tuple, Set
import traceback
import logging
import streamlit as st

from src.state import get_ideas, get_central, set_central, get_next_id, increment_next_id, add_idea, set_ideas, get_store, save_data
from src.utils import is_circular, validate_node_exists, validate_payload, extract_canvas_coordinates, standard_response
from src.ui.canvas import handle_canvas_interaction
from src.history import save_state_to_history
from src.node_utils import validate_node, update_node_position_service
from src.message_format import Message

# Get logger
logger = logging.getLogger(__name__)

# Handler registry
_handlers = {}

def register_handler(action: str, handler_func: Callable) -> None:
    """Register a handler function for a specific action."""
    _handlers[action] = handler_func

def get_handler(action: str) -> Optional[Callable]:
    """Get the registered handler for an action."""
    return _handlers.get(action)

def is_registered_action(action: str) -> bool:
    """Check if an action has a registered handler."""
    return action in _handlers

# Node-related handler functions

def handle_add_node(message: Message) -> Dict[str, Any]:
    """Handle adding a new node."""
    try:
        # Validate the node data
        if not validate_payload(message.payload, required_fields=['label']):
            return standard_response(message, False, 'Invalid node data: missing required field "label"')
            
        # Create new node
        node_data = {
            'label': message.payload.get('label', 'New Node'),
            'description': message.payload.get('description', ''),
            'tag': message.payload.get('tag', ''),
            'urgency': message.payload.get('urgency', 'medium'),
            'edge_type': message.payload.get('edge_type', 'default'),
            'parent': message.payload.get('parent', get_central()),
        }
        
        # Save current state for undo
        save_state_to_history()
        
        # Add the node
        add_idea(node_data)
        
        # Get the newly created node to return its ID
        ideas = get_ideas()
        new_node = ideas[-1] if ideas else None
        
        if new_node:
            return standard_response(message, True, f'Node added successfully with ID: {new_node["id"]}', {'node_id': new_node['id']})
        else:
            return standard_response(message, False, 'Error adding node: node not found after addition')
            
    except Exception as e:
        error_msg = f"Error adding node: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return standard_response(message, False, error_msg)

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
        error_msg = handle_error(e, logger, "Error processing delete node request")
        return standard_response(message, False, error_msg)

def handle_reparent_node(message: Message) -> Dict[str, Any]:
    """Handle node reparenting requests."""
    try:
        ideas = get_ideas()
        save_state_to_history()
        
        # Validate payload
        is_valid, error_msg, validated_payload = validate_payload(
            message.payload,
            required_fields=['id', 'parent_id'],
            field_types={'id': int, 'parent_id': int}
        )
        
        if not is_valid:
            logger.warning(error_msg)
            return standard_response(message, False, error_msg)
        
        node_id = validated_payload['id']
        parent_id = validated_payload['parent_id']
        
        # Validate both nodes exist
        success, node, error_msg = validate_node_exists(node_id, ideas, 'reparent')
        if not success:
            return standard_response(message, False, error_msg)
            
        # For parent_id, None is valid (means making it a root node)
        if parent_id is not None:
            success, parent_node, error_msg = validate_node_exists(parent_id, ideas, 'parent')
            if not success:
                return standard_response(message, False, error_msg)
            
            # Check for circular references
            if is_circular(node_id, parent_id, ideas):
                logger.warning(f"Attempted circular reference: node {node_id} -> parent {parent_id}")
                return standard_response(message, False, "Cannot create circular reference")
        
        # Update the node's parent
        node['parent'] = parent_id
        
        # Set edge type
        if 'edge_type' in validated_payload:
            node['edge_type'] = validated_payload['edge_type']
        elif parent_id is not None:
            # Default edge type if not specified
            if 'edge_type' not in node:
                node['edge_type'] = 'default'
        
        # Save changes to data file
        logger.debug(f"Saving after reparenting node {node_id} to parent {parent_id}")
        set_ideas(ideas)
        save_data(get_store())
        
        st.rerun()
        return standard_response(message, True)
    except Exception as e:
        error_msg = handle_error(e, logger, "Error processing reparent request")
        return standard_response(message, False, error_msg)

def handle_new_node(message: Message) -> Dict[str, Any]:
    """Handle node creation requests."""
    try:
        # Get the central node for default parent
        central = get_central()
        ideas = get_ideas()
        save_state_to_history()
        
        # Validate payload with field name compatibility
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
        
        if action in _handlers:
            return _handlers[action](message)
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