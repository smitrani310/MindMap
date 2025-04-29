# Message/event handlers and error handling for MindMap
import streamlit as st
from src.state import get_ideas, get_central, set_central, get_next_id, increment_next_id, add_idea, set_ideas
from src.history import save_state_to_history, perform_undo, perform_redo
from src.utils import recalc_size

def handle_exception(e):
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

def is_circular(child_id, parent_id, nodes):
    if child_id == parent_id:
        return True
    current_id = parent_id
    visited = set([current_id])
    while True:
        parent_node = next((n for n in nodes if n['id'] == current_id), None)
        if not parent_node or parent_node.get('parent') is None:
            return False
        current_id = parent_node['parent']
        if current_id in visited:
            return True
        if current_id == child_id:
            return True
        visited.add(current_id)

def handle_message(msg_data):
    try:
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
            for k, v in pl.items():
                try:
                    node_id = int(k)
                    node = next((n for n in ideas if n['id'] == node_id), None)
                    if node:
                        node['x'], node['y'] = v['x'], v['y']
                except (ValueError, TypeError) as e:
                    st.error(f"Invalid node ID: {k}")
        elif action == 'edit_modal':
            st.session_state['edit_node'] = int(pl['id'])
            st.rerun()
        elif action == 'delete':
            save_state_to_history()
            node_id = int(pl['id'])
            to_remove = set()
            def collect_descendants(node_id):
                to_remove.add(node_id)
                for child in [n for n in ideas if n.get('parent') == node_id]:
                    collect_descendants(child['id'])
            collect_descendants(node_id)
            set_ideas([n for n in ideas if n['id'] not in to_remove])
            if get_central() in to_remove:
                set_central(None)
            st.rerun()
        elif action == 'reparent':
            save_state_to_history()
            child_id = int(pl['id'])
            parent_id = int(pl['parent'])
            child = next((n for n in ideas if n['id'] == child_id), None)
            if is_circular(child_id, parent_id, ideas):
                st.warning("Cannot create circular parent-child relationships")
                return
            if child and parent_id in {n['id'] for n in ideas}:
                child['parent'] = parent_id
                if not child.get('edge_type'):
                    child['edge_type'] = 'default'
                st.rerun()
        elif action == 'new_node':
            save_state_to_history()
            central = get_central()
            new_node = {
                'id': get_next_id(),
                'label': pl['label'],
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
            st.rerun()
    except Exception as e:
        handle_exception(e) 