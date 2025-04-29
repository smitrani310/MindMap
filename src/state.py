# State management helpers for MindMap

def get_store():
    import streamlit as st
    if 'store' not in st.session_state:
        st.session_state['store'] = {
            'ideas': [],
            'central': None,
            'next_id': 0,
            'history': [],
            'history_index': -1,
            'current_theme': 'default'
        }
    return st.session_state['store']

def get_ideas():
    return get_store()['ideas']

def set_ideas(ideas):
    store = get_store()
    from src.history import save_state_to_history
    save_state_to_history()
    store['ideas'] = ideas

def add_idea(node):
    store = get_store()
    from src.history import save_state_to_history
    save_state_to_history()
    store['ideas'].append(node)

def get_central():
    return get_store()['central']

def set_central(mid):
    from src.history import save_state_to_history
    save_state_to_history()
    get_store()['central'] = mid

def get_next_id():
    return get_store()['next_id']

def increment_next_id():
    store = get_store()
    store['next_id'] += 1

def get_current_theme():
    return get_store().get('current_theme', 'default')

def set_current_theme(theme_name):
    get_store()['current_theme'] = theme_name 