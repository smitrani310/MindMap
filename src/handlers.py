# Message/event handlers and error handling for MindMap
import streamlit as st
import logging
from src.state import get_ideas, get_central, set_central, get_next_id, increment_next_id, add_idea, set_ideas, get_store, save_data
from src.history import save_state_to_history, perform_undo, perform_redo
from src.utils import recalc_size, collect_descendants, find_node_by_id, find_closest_node, handle_error, validate_node_exists
from src.message_format import Message, validate_message, create_response_message
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from src.node_utils import update_node_position, update_node_position_service
import traceback

logger = logging.getLogger(__name__)

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

        # Get current ideas
        ideas = get_ideas()
        
        # Process different action types
        if message.action == 'canvas_click':
            try:
                # Extract click coordinates
                click_x = message.payload.get('x', 0)
                click_y = message.payload.get('y', 0)
                canvas_width = message.payload.get('canvasWidth', 800)
                canvas_height = message.payload.get('canvasHeight', 600)
                
                # Use utility function to find the closest node
                closest_node, min_distance, click_threshold = find_closest_node(
                    ideas, click_x, click_y, canvas_width, canvas_height
                )
                
                if closest_node and min_distance <= click_threshold:
                    # Select the node
                    st.session_state['selected_node'] = closest_node['id']
                    st.rerun()
                    return create_response_message(message, 'completed')
                else:
                    logger.warning(f"No node found near click coordinates (closest: {closest_node['label'] if closest_node else 'None'} at distance: {min_distance:.2f}, threshold: {click_threshold:.2f})")
                    return create_response_message(message, 'failed', 'No node found near click coordinates')
                    
            except Exception as e:
                error_msg = handle_error(e, logger, "Error processing canvas click")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'canvas_dblclick':
            try:
                # Extract click coordinates
                click_x = message.payload.get('x', 0)
                click_y = message.payload.get('y', 0)
                canvas_width = message.payload.get('canvasWidth', 800)
                canvas_height = message.payload.get('canvasHeight', 600)
                
                # Use utility function to find the closest node
                closest_node, min_distance, click_threshold = find_closest_node(
                    ideas, click_x, click_y, canvas_width, canvas_height
                )
                
                if closest_node and min_distance <= click_threshold:
                    # Open edit modal for the node
                    st.session_state['edit_node'] = closest_node['id']
                    st.rerun()
                    return create_response_message(message, 'completed')
                else:
                    logger.warning(f"No node found near double-click coordinates")
                    return create_response_message(message, 'failed', 'No node found near double-click coordinates')
                    
            except Exception as e:
                error_msg = handle_error(e, logger, "Error processing canvas double-click")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'canvas_contextmenu':
            try:
                # Extract click coordinates
                click_x = message.payload.get('x', 0)
                click_y = message.payload.get('y', 0)
                canvas_width = message.payload.get('canvasWidth', 800)
                canvas_height = message.payload.get('canvasHeight', 600)
                
                # Use utility function to find the closest node
                closest_node, min_distance, click_threshold = find_closest_node(
                    ideas, click_x, click_y, canvas_width, canvas_height
                )
                
                if closest_node and min_distance <= click_threshold:
                    # Delete the node
                    save_state_to_history()
                    ideas.remove(closest_node)
                    set_ideas(ideas)
                    save_data(get_store())
                    st.rerun()
                    return create_response_message(message, 'completed')
                else:
                    logger.warning(f"No node found near context menu coordinates")
                    return create_response_message(message, 'failed', 'No node found near context menu coordinates')
                    
            except Exception as e:
                error_msg = handle_error(e, logger, "Error processing canvas context menu")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'undo':
            if perform_undo():
                st.rerun()
            return create_response_message(message, 'completed')
            
        elif message.action == 'redo':
            if perform_redo():
                st.rerun()
            return create_response_message(message, 'completed')
            
        elif message.action == 'pos':
            try:
                # Log the payload for debugging
                logger.debug(f"Position update payload in handlers.py: {message.payload}")
                
                # Check for direct format (id, x, y)
                node_id = message.payload.get('id')
                new_x = message.payload.get('x')
                new_y = message.payload.get('y')
                
                if node_id is not None and new_x is not None and new_y is not None:
                    # Direct format - use the position service
                    logger.info(f"Using position service to update node {node_id} to ({new_x}, {new_y})")
                    
                    result = update_node_position_service(
                        node_id=node_id,
                        x=new_x,
                        y=new_y,
                        get_ideas_func=get_ideas,
                        set_ideas_func=set_ideas,
                        save_state_func=save_state_to_history,
                        save_data_func=save_data,
                        get_store_func=get_store
                    )
                    
                    if result['success']:
                        logger.info(f"Position update success: {result['message']}")
                        return create_response_message(message, 'completed')
                    else:
                        logger.warning(f"Position update failed: {result['message']}")
                        return create_response_message(message, 'failed', result['message'])
                        
                else:
                    # Object format - multiple nodes at once
                    position_updated = False
                    results = []
                    
                    # Check each key in the payload for node IDs
                    for k, v in message.payload.items():
                        # Skip known non-ID keys
                        if k in ('source', 'action', 'timestamp', 'message_id'):
                            continue
                            
                        # Check if this is a node position update
                        if isinstance(v, dict) and 'x' in v and 'y' in v:
                            logger.info(f"Using position service to update node {k} to ({v['x']}, {v['y']})")
                            
                            result = update_node_position_service(
                                node_id=k,
                                x=v['x'],
                                y=v['y'],
                                get_ideas_func=get_ideas,
                                set_ideas_func=set_ideas,
                                save_state_func=save_state_to_history,
                                save_data_func=save_data,
                                get_store_func=get_store
                            )
                            
                            results.append(result)
                            if result['success']:
                                position_updated = True
                    
                    # Return overall status based on results
                    if position_updated:
                        logger.info("Successfully updated one or more node positions")
                        return create_response_message(message, 'completed')
                    else:
                        error_messages = [r['message'] for r in results if not r['success']]
                        logger.warning(f"No positions were updated: {error_messages}")
                        return create_response_message(message, 'failed', "No positions were updated")
                        
            except Exception as e:
                error_msg = handle_error(e, logger, "Error processing position update")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'edit_modal':
            try:
                node_id = int(message.payload['id'])
                if node_id in {n['id'] for n in ideas}:
                    st.session_state['edit_node'] = node_id
                    st.rerun()
                    return create_response_message(message, 'completed')
                else:
                    logger.warning(f"Edit request for nonexistent node: {node_id}")
                    return create_response_message(message, 'failed', 'Node not found')
            except (ValueError, TypeError, KeyError) as e:
                error_msg = handle_error(e, logger, "Invalid edit modal request")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'select_node':
            try:
                node_id = int(message.payload['id'])
                logger.info(f"Processing select_node action for node ID: {node_id}")
                
                # Use the validation utility
                success, node, error_msg = validate_node_exists(node_id, ideas, 'select')
                if success:
                    logger.info(f"Node {node_id} found, setting as selected node")
                    st.session_state['selected_node'] = node_id
                    st.rerun()
                    return create_response_message(message, 'completed')
                else:
                    logger.warning(error_msg)
                    return create_response_message(message, 'failed', 'Node not found')
            except (ValueError, TypeError, KeyError) as e:
                error_msg = handle_error(e, logger, "Invalid select node request")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'center_node':
            try:
                node_id = int(message.payload['id'])
                
                # Use the validation utility
                success, node, error_msg = validate_node_exists(node_id, ideas, 'center')
                if success:
                    set_central(node_id)
                    st.rerun()
                    return create_response_message(message, 'completed')
                else:
                    logger.warning(error_msg)
                    return create_response_message(message, 'failed', 'Node not found')
            except (ValueError, TypeError, KeyError) as e:
                error_msg = handle_error(e, logger, "Invalid center node request")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'delete' or message.action == 'delete_node':
            try:
                save_state_to_history()
                # Handle both 'id' and 'node_id' in payload for compatibility
                node_id = int(message.payload.get('id', message.payload.get('node_id')))
                
                # Use the validation utility
                success, node, error_msg = validate_node_exists(node_id, ideas, 'delete')
                if not success:
                    logger.warning(error_msg)
                    return create_response_message(message, 'failed', 'Node not found')
                    
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
                return create_response_message(message, 'completed')
            except (ValueError, TypeError, KeyError) as e:
                error_msg = handle_error(e, logger, "Invalid delete request")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'reparent':
            try:
                save_state_to_history()
                child_id = int(message.payload['id'])
                parent_id = int(message.payload['parent'])
                
                # Validate that both nodes exist
                child_success, child, child_error = validate_node_exists(child_id, ideas, 'reparent child')
                if not child_success:
                    logger.warning(child_error)
                    return create_response_message(message, 'failed', 'Child node not found')
                
                parent_success, parent, parent_error = validate_node_exists(parent_id, ideas, 'reparent parent')
                if not parent_success:
                    logger.warning(parent_error)
                    return create_response_message(message, 'failed', 'Parent node not found')
                
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
                error_msg = handle_error(e, logger, "Invalid reparent request")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'new_node' or message.action == 'create_node':
            try:
                save_state_to_history()
                central = get_central()
                
                # Map the payload fields for compatibility
                label = message.payload.get('label', message.payload.get('title', ''))
                description = message.payload.get('description', '')
                
                # Validate label
                if not label:
                    logger.warning("New node request with empty label")
                    return create_response_message(message, 'failed', 'New node request with empty label')
                    
                new_node = {
                    'id': get_next_id(),
                    'label': label.strip(),
                    'description': description,
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
                return create_response_message(message, 'completed', None, {'node_id': new_node['id']})
            except (KeyError, ValueError) as e:
                error_msg = handle_error(e, logger, "Invalid new node request")
                return create_response_message(message, 'failed', error_msg)
                
        elif message.action == 'edit_node':
            try:
                save_state_to_history()
                # Handle both 'node_id' and 'id' in payload for compatibility
                node_id = int(message.payload.get('node_id', message.payload.get('id')))
                
                # Use the validation utility
                success, node, error_msg = validate_node_exists(node_id, ideas, 'edit')
                if not success:
                    logger.warning(error_msg)
                    return create_response_message(message, 'failed', 'Node not found')

                # Update node properties with field name compatibility
                if 'label' in message.payload or 'title' in message.payload:
                    node['label'] = message.payload.get('label', message.payload.get('title')).strip()
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
                error_msg = handle_error(e, logger, "Invalid edit request")
                return create_response_message(message, 'failed', error_msg)
        else:
            logger.warning(f"Unknown action type: {message.action}")
            return create_response_message(message, 'failed', 'Unknown action type')
            
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