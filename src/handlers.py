# Message/event handlers and error handling for MindMap
import streamlit as st
import logging
from src.state import get_ideas, get_central, set_central, get_next_id, increment_next_id, add_idea, set_ideas, get_store, save_data
from src.history import save_state_to_history, perform_undo, perform_redo
from src.utils import recalc_size

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
    """Handle messages from the client."""
    try:
        # Validate required fields
        if not isinstance(msg_data, dict) or 'type' not in msg_data or 'payload' not in msg_data:
            logger.error(f"Invalid message format: {msg_data}")
            return
            
        action, pl = msg_data['type'], msg_data['payload']
        ideas = get_ideas()
        
        if action == 'undo':
            if perform_undo():
                st.rerun()
        elif action == 'redo':
            if perform_redo():
                st.rerun()
        elif action == 'pos':
            save_state_to_history()
            position_updated = False
            for k, v in pl.items():
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
        elif action == 'edit_modal':
            try:
                node_id = int(pl['id'])
                if node_id in {n['id'] for n in ideas}:
                    st.session_state['edit_node'] = node_id
                    st.rerun()
                else:
                    logger.warning(f"Edit request for nonexistent node: {node_id}")
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Invalid edit modal request: {pl}")
        elif action == 'select_node':
            try:
                node_id = int(pl['id'])
                logger.info(f"Processing select_node action for node ID: {node_id}")
                if node_id in {n['id'] for n in ideas}:
                    logger.info(f"Node {node_id} found, setting as selected node")
                    st.session_state['selected_node'] = node_id
                    st.rerun()
                else:
                    logger.warning(f"Select request for nonexistent node: {node_id}")
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Invalid select node request: {pl}, Error: {str(e)}")
        elif action == 'center_node':
            try:
                node_id = int(pl['id'])
                if node_id in {n['id'] for n in ideas}:
                    set_central(node_id)
                    st.rerun()
                else:
                    logger.warning(f"Center request for nonexistent node: {node_id}")
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Invalid center node request: {pl}")
        elif action == 'delete':
            try:
                save_state_to_history()
                node_id = int(pl['id'])
                if node_id not in {n['id'] for n in ideas}:
                    logger.warning(f"Delete request for nonexistent node: {node_id}")
                    return
                    
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
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Invalid delete request: {pl}")
        elif action == 'reparent':
            try:
                save_state_to_history()
                child_id = int(pl['id'])
                parent_id = int(pl['parent'])
                
                # Validate that both nodes exist
                if child_id not in {n['id'] for n in ideas}:
                    logger.warning(f"Reparent request for nonexistent child: {child_id}")
                    return
                
                if parent_id not in {n['id'] for n in ideas}:
                    logger.warning(f"Reparent request for nonexistent parent: {parent_id}")
                    return
                
                child = next((n for n in ideas if n['id'] == child_id), None)
                
                if is_circular(child_id, parent_id, ideas):
                    logger.warning(f"Circular reference detected: {child_id} -> {parent_id}")
                    st.warning("Cannot create circular parent-child relationships")
                    return
                    
                child['parent'] = parent_id
                if not child.get('edge_type'):
                    child['edge_type'] = 'default'
                
                # Save changes to data file
                logger.debug(f"Saving after reparenting node {child_id} to parent {parent_id}")
                save_data(get_store())
                    
                st.rerun()
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Invalid reparent request: {pl}")
        elif action == 'new_node':
            try:
                save_state_to_history()
                central = get_central()
                
                # Validate label
                if not pl.get('label'):
                    logger.warning("New node request with empty label")
                    return
                    
                new_node = {
                    'id': get_next_id(),
                    'label': pl['label'].strip(),
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
            except (KeyError, ValueError) as e:
                logger.error(f"Invalid new node request: {pl}")
        else:
            logger.warning(f"Unknown action type: {action}")
    except Exception as e:
        handle_exception(e) 