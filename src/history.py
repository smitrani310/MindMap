# Undo/redo and history management for MindMap
from copy import deepcopy
from src.state import get_store

def save_state_to_history():
    store = get_store()
    if len(store['ideas']) > 0 or store['history_index'] >= 0:
        if store['history_index'] < len(store['history']) - 1:
            store['history'] = store['history'][:store['history_index'] + 1]
        current_state = {
            'ideas': deepcopy(store['ideas']),
            'central': store['central']
        }
        store['history'].append(current_state)
        store['history_index'] = len(store['history']) - 1
        max_history = 30
        if len(store['history']) > max_history:
            store['history'] = store['history'][-max_history:]
            store['history_index'] = len(store['history']) - 1

def can_undo():
    store = get_store()
    return store['history_index'] > 0

def can_redo():
    store = get_store()
    return 0 <= store['history_index'] < len(store['history']) - 1

def perform_undo():
    store = get_store()
    if can_undo():
        store['history_index'] -= 1
        previous_state = store['history'][store['history_index']]
        store['ideas'] = deepcopy(previous_state['ideas'])
        store['central'] = previous_state['central']
        return True
    return False

def perform_redo():
    store = get_store()
    if can_redo():
        store['history_index'] += 1
        next_state = store['history'][store['history_index']]
        store['ideas'] = deepcopy(next_state['ideas'])
        store['central'] = next_state['central']
        return True
    return False 