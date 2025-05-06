# Message/event handlers and error handling for MindMap
import streamlit as st
import logging
from src.state import get_ideas, get_central, set_central, get_next_id, increment_next_id, add_idea, set_ideas, get_store, save_data
from src.history import save_state_to_history, perform_undo, perform_redo
from src.utils import recalc_size
from src.message_format import Message, validate_message, create_response_message

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
        parent_node = next((n for n in nodes if n['id'] == current_id), None)
        if not parent_node:
            return False
            
        current_id = parent_node.get('parent')
        
    return False

def handle_message(msg_data):
    """Handle messages from the client using standardized message format."""
    try:
        # Validate message format
        if not validate_message(msg_data):
            logger.error(f"Invalid message format: {msg_data}")
            return create_response_message(
                Message.from_dict(msg_data),
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
                
                # Find the nearest node
                closest_node = None
                min_distance = float('inf')
                
                for node in ideas:
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
                
        elif message.action == 'canvas_dblclick':
            try:
                # Extract click coordinates
                click_x = message.payload.get('x', 0)
                click_y = message.payload.get('y', 0)
                canvas_width = message.payload.get('canvasWidth', 800)
                canvas_height = message.payload.get('canvasHeight', 600)
                
                # Find the nearest node
                closest_node = None
                min_distance = float('inf')
                
                for node in ideas:
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
                
        elif message.action == 'canvas_contextmenu':
            try:
                # Extract click coordinates
                click_x = message.payload.get('x', 0)
                click_y = message.payload.get('y', 0)
                canvas_width = message.payload.get('canvasWidth', 800)
                canvas_height = message.payload.get('canvasHeight', 600)
                
                # Find the nearest node
                closest_node = None
                min_distance = float('inf')
                
                for node in ideas:
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
                save_state_to_history()
                position_updated = False
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
                    save_data(get_store())
                return create_response_message(message, 'completed')
            except Exception as e:
                logger.error(f"Error processing position update: {str(e)}")
                return create_response_message(message, 'failed', str(e))
                
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
                logger.error(f"Invalid edit modal request: {message.payload}")
                return create_response_message(message, 'failed', str(e))
                
        elif message.action == 'select_node':
            try:
                node_id = int(message.payload['id'])
                logger.info(f"Processing select_node action for node ID: {node_id}")
                if node_id in {n['id'] for n in ideas}:
                    logger.info(f"Node {node_id} found, setting as selected node")
                    st.session_state['selected_node'] = node_id
                    st.rerun()
                    return create_response_message(message, 'completed')
                else:
                    logger.warning(f"Select request for nonexistent node: {node_id}")
                    return create_response_message(message, 'failed', 'Node not found')
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Invalid select node request: {message.payload}")
                return create_response_message(message, 'failed', str(e))
                
        elif message.action == 'center_node':
            try:
                node_id = int(message.payload['id'])
                if node_id in {n['id'] for n in ideas}:
                    set_central(node_id)
                    st.rerun()
                    return create_response_message(message, 'completed')
                else:
                    logger.warning(f"Center request for nonexistent node: {node_id}")
                    return create_response_message(message, 'failed', 'Node not found')
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Invalid center node request: {message.payload}")
                return create_response_message(message, 'failed', str(e))
                
        elif message.action == 'delete':
            try:
                save_state_to_history()
                node_id = int(message.payload['id'])
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
        elif message.action == 'reparent':
            try:
                save_state_to_history()
                child_id = int(message.payload['id'])
                parent_id = int(message.payload['parent'])
                
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
                save_data(get_store())
                    
                st.rerun()
                return create_response_message(message, 'completed')
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Invalid reparent request: {message.payload}")
                return create_response_message(message, 'failed', str(e))
        elif message.action == 'new_node':
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
                    'description': '',
                    'urgency': 'medium',
                    'tag': '',
                    'parent': central,
                    'edge_type': 'default' if central is not None else None,
                    'x': None,
                    'y': None
                }
                recalc_size(new_node)
                add_idea(new_node)
                increment_next_id()
                
                # Save changes to data file
                logger.debug(f"Saving after creating new node with ID {new_node['id']}")
                save_data(get_store())
                
                st.rerun()
                return create_response_message(message, 'completed')
            except (KeyError, ValueError) as e:
                logger.error(f"Invalid new node request: {message.payload}")
                return create_response_message(message, 'failed', str(e))
        else:
            logger.warning(f"Unknown action type: {message.action}")
            return create_response_message(message, 'failed', 'Unknown action type')
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return create_response_message(message, 'failed', str(e)) 