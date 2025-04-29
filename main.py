"""streamlit_mindmap_app.py – v5.2 Enhanced Mind Map with Stability Improvements
Added features:
- Native component messaging for smoother UI updates
- JS stability & cleanup with proper error handling
- Explicit circular-parent checks to prevent loops
- Centralized error handling
- Strict integer ID management & traceability

Original features:
- Tags/categories for nodes with color coding
- Node descriptions/notes
- Different connection types
- Undo/redo functionality
- Custom themes
- Keyboard shortcuts
- Search and replace
"""

import json
import textwrap
import datetime
import traceback
from typing import List, Dict, Optional, Tuple, Set
from copy import deepcopy

import streamlit as st
from pyvis.network import Network
import streamlit.components.v1 as components

# Import refactored modules
from src.state import get_store, get_ideas, set_ideas, add_idea, get_central, set_central, get_next_id, increment_next_id, get_current_theme, set_current_theme
from src.history import save_state_to_history, can_undo, can_redo, perform_undo, perform_redo
from src.utils import hex_to_rgb, get_theme, recalc_size, get_edge_color, get_urgency_color, get_tag_color
from src.themes import THEMES, TAGS, URGENCY_SIZE, PRIMARY_NODE_BORDER, RGBA_ALPHA
from src.handlers import handle_message, handle_exception

# ---------------- State Management Helpers ----------------

def get_store() -> Dict:
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

def get_ideas() -> List[Dict]:
    return get_store()['ideas']

def set_ideas(ideas: List[Dict]):
    store = get_store()
    # Save current state to history before changing
    save_state_to_history()
    store['ideas'] = ideas

def add_idea(node: Dict):
    store = get_store()
    # Save current state to history before changing
    save_state_to_history()
    store['ideas'].append(node)

def get_central() -> Optional[int]:
    return get_store()['central']

def set_central(mid: Optional[int]):
    save_state_to_history()
    get_store()['central'] = mid

def get_next_id() -> int:
    return get_store()['next_id']

def increment_next_id():
    store = get_store()
    store['next_id'] += 1

def get_current_theme() -> str:
    return get_store().get('current_theme', 'default')

def set_current_theme(theme_name: str):
    get_store()['current_theme'] = theme_name

# ---------------- Error Handling ----------------

def handle_exception(e):
    """Centralized error handling"""
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

# ---------------- Circular Reference Check ----------------

def is_circular(child_id: int, parent_id: int, nodes: List[Dict]) -> bool:
    """Check if making child_id a child of parent_id would create a circular reference"""
    if child_id == parent_id:
        return True

    # Walk up the parent chain to check if child_id appears
    current_id = parent_id
    visited = set([current_id])

    while True:
        parent_node = next((n for n in nodes if n['id'] == current_id), None)
        if not parent_node or parent_node.get('parent') is None:
            return False

        current_id = parent_node['parent']

        # If we've seen this ID before, there's already a cycle
        if current_id in visited:
            return True

        # If the current parent is the child we're checking, it would create a cycle
        if current_id == child_id:
            return True

        visited.add(current_id)

# ---------------- History Management for Undo/Redo ----------------

def save_state_to_history():
    """Save current state to history for undo/redo functionality"""
    store = get_store()
    # Only save if we have something to save
    if len(store['ideas']) > 0 or store['history_index'] >= 0:
        # If we're not at the end of history, truncate future history
        if store['history_index'] < len(store['history']) - 1:
            store['history'] = store['history'][:store['history_index'] + 1]

        # Create a deep copy of the current state
        current_state = {
            'ideas': deepcopy(store['ideas']),
            'central': store['central']
        }

        # Add to history and update index
        store['history'].append(current_state)
        store['history_index'] = len(store['history']) - 1

        # Limit history size to avoid memory issues
        max_history = 30
        if len(store['history']) > max_history:
            store['history'] = store['history'][-max_history:]
            store['history_index'] = len(store['history']) - 1

def can_undo() -> bool:
    """Check if undo is available"""
    store = get_store()
    return store['history_index'] > 0

def can_redo() -> bool:
    """Check if redo is available"""
    store = get_store()
    return 0 <= store['history_index'] < len(store['history']) - 1

def perform_undo():
    """Restore previous state from history"""
    store = get_store()
    if can_undo():
        store['history_index'] -= 1
        previous_state = store['history'][store['history_index']]
        store['ideas'] = deepcopy(previous_state['ideas'])
        store['central'] = previous_state['central']
        return True
    return False

def perform_redo():
    """Restore next state from history"""
    store = get_store()
    if can_redo():
        store['history_index'] += 1
        next_state = store['history'][store['history_index']]
        store['ideas'] = deepcopy(next_state['ideas'])
        store['central'] = next_state['central']
        return True
    return False

# ---------------- Constants & Helpers ----------------
RGBA_ALPHA = 0.5

# Predefined themes
THEMES = {
    'default': {
        'background': '#FFFFFF',
        'urgency_colors': {'high': '#e63946', 'medium': '#f4a261', 'low': '#2a9d8f'},
        'edge_colors': {'default': '#848484', 'supports': '#2a9d8f', 'contradicts': '#e63946', 'relates': '#f4a261'}
    },
    'dark': {
        'background': '#2E3440',
        'urgency_colors': {'high': '#BF616A', 'medium': '#EBCB8B', 'low': '#A3BE8C'},
        'edge_colors': {'default': '#D8DEE9', 'supports': '#A3BE8C', 'contradicts': '#BF616A', 'relates': '#EBCB8B'}
    },
    'pastel': {
        'background': '#F8F9FA',
        'urgency_colors': {'high': '#FF9AA2', 'medium': '#FFB347', 'low': '#98DDCA'},
        'edge_colors': {'default': '#9BA4B4', 'supports': '#98DDCA', 'contradicts': '#FF9AA2', 'relates': '#FFB347'}
    },
    'vibrant': {
        'background': '#FFFFFF',
        'urgency_colors': {'high': '#FF1E56', 'medium': '#FFAC41', 'low': '#16C79A'},
        'edge_colors': {'default': '#666666', 'supports': '#16C79A', 'contradicts': '#FF1E56', 'relates': '#FFAC41'}
    }
}

# Tags with colors
TAGS = {
    'idea': '#4361EE',
    'task': '#3A0CA3',
    'question': '#7209B7',
    'project': '#F72585',
    'note': '#4CC9F0',
    'research': '#560BAD',
    'personal': '#F3722C',
    'work': '#F8961E'
}

URGENCY_SIZE = {'high': 300, 'medium': 200, 'low': 120}
PRIMARY_NODE_BORDER = 4
hex_to_rgb = lambda h: tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def get_theme():
    """Get the current theme colors"""
    return THEMES[get_current_theme()]

def recalc_size(node: Dict):
    """Calculate the size of a node based on urgency"""
    node['size'] = URGENCY_SIZE.get(node.get('urgency', 'low'), 120)

def get_edge_color(edge_type: str) -> str:
    """Get the color for an edge based on relationship type"""
    return get_theme()['edge_colors'].get(edge_type, get_theme()['edge_colors']['default'])

def get_urgency_color(urgency: str) -> str:
    """Get the color for a node based on urgency"""
    return get_theme()['urgency_colors'].get(urgency, get_theme()['urgency_colors']['low'])

def get_tag_color(tag: str) -> str:
    """Get the color for a tag"""
    return TAGS.get(tag, '#808080')  # Default gray for unknown tags

# ---------------- Message Handling ----------------

def handle_message(msg_data):
    """Process messages from the JavaScript frontend"""
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

            # Get node and all its descendants
            to_remove = set()

            def collect_descendants(node_id):
                to_remove.add(node_id)
                for child in [n for n in ideas if n.get('parent') == node_id]:
                    collect_descendants(child['id'])

            collect_descendants(node_id)

            # Remove collected nodes
            set_ideas([n for n in ideas if n['id'] not in to_remove])
            if get_central() in to_remove:
                set_central(None)
            st.rerun()  # Force rerun after deletion

        elif action == 'reparent':
            save_state_to_history()
            child_id = int(pl['id'])
            parent_id = int(pl['parent'])

            child = next((n for n in ideas if n['id'] == child_id), None)

            # Check for circular references
            if is_circular(child_id, parent_id, ideas):
                st.warning("Cannot create circular parent-child relationships")
                return

            if child and parent_id in {n['id'] for n in ideas}:
                child['parent'] = parent_id
                # Keep the edge type or set to default if none
                if not child.get('edge_type'):
                    child['edge_type'] = 'default'
                st.rerun()  # Force rerun after reparenting

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
            st.rerun()  # Force rerun to refresh UI

    except Exception as e:
        handle_exception(e)

# ---------------- Main App ----------------
try:
    st.set_page_config(page_title="Enhanced Mind Map", layout="wide")

    # Apply theme to page
    current_theme = get_current_theme()
    if current_theme == 'dark':
        st.markdown("""
        <style>
        .stApp {
            background-color: #2E3440;
            color: #D8DEE9;
        }
        .stSidebar {
            background-color: #3B4252;
        }
        </style>
        """, unsafe_allow_html=True)

    st.title("🧠 Enhanced Mind Map")

    # Sidebar Theme Selection
    with st.sidebar.expander("Settings", expanded=False):
        selected_theme = st.selectbox(
            "Select Theme",
            options=list(THEMES.keys()),
            index=list(THEMES.keys()).index(get_current_theme())
        )
        
        # Add connection length slider
        edge_length = st.slider(
            "Connection Length", 
            min_value=50, 
            max_value=300, 
            value=100, 
            step=10,
            help="Adjust the length of connections between nodes"
        )
        
        # Add spring strength slider
        spring_strength = st.slider(
            "Connection Strength",
            min_value=0.1,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="Adjust how strongly connected nodes pull together (higher = tighter grouping)"
        )
        
        # Add size multiplier for urgency differences
        size_multiplier = st.slider(
            "Urgency Size Impact",
            min_value=1.0,
            max_value=3.0,
            value=1.0,
            step=0.2,
            help="Enhance the size difference between urgency levels (higher = more pronounced difference)"
        )
        
        if selected_theme != get_current_theme():
            set_current_theme(selected_theme)
            st.rerun()

    # Sidebar Search
    search_col1, search_col2 = st.sidebar.columns([3, 1])
    search_q = search_col1.text_input("🔍 Search nodes")
    search_replace = search_col2.checkbox("Replace")

    if search_replace and search_q:
        replace_q = st.sidebar.text_input("Replace with")
        if st.sidebar.button("Replace All"):
            ideas = get_ideas()
            if ideas:
                save_state_to_history()
                count = 0
                for node in ideas:
                    if search_q.lower() in node['label'].lower():
                        node['label'] = node['label'].replace(search_q, replace_q)
                        count += 1
                    if 'description' in node and search_q.lower() in node['description'].lower():
                        node['description'] = node['description'].replace(search_q, replace_q)
                        count += 1
                st.sidebar.success(f"Replaced {count} instances")
                if count > 0:
                    st.rerun()

    # Import / Export JSON
    with st.sidebar.expander("📂 Import / Export"):
        uploaded = st.file_uploader("Import JSON", type="json")
        if uploaded:
            try:
                data = json.load(uploaded)
                if not isinstance(data, list):
                    st.error("JSON must be a list")
                else:
                    save_state_to_history()  # Save current state before import
                    label_map = {item['label'].strip().lower(): item['id'] for item in data}
                    for item in data:
                        item.setdefault('x', None)
                        item.setdefault('y', None)
                        item.setdefault('description', '')
                        item.setdefault('tag', '')
                        item.setdefault('edge_type', 'default')
                        p = item.get('parent')
                        if isinstance(p, str):
                            item['parent'] = label_map.get(p.strip().lower())
                        recalc_size(item)
                    set_ideas(data)
                    get_store()['next_id'] = max((i['id'] for i in data), default=-1) + 1
                    set_central(next((i['id'] for i in data if i.get('is_central')), None))
                    st.success("Imported bubbles from JSON")
            except Exception as e:
                handle_exception(e)

        ideas = get_ideas()
        if ideas:
            export = [item.copy() for item in ideas]
            for item in export:
                item['is_central'] = (item['id'] == get_central())
            st.download_button(
                "💾 Export JSON",
                data=json.dumps(export, indent=2),
                file_name=f"mindmap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    # Add Bubble Form
    with st.sidebar.form("add_bubble_form"):
        st.header("➕ Add Bubble")
        label = st.text_input("Label")
        description = st.text_area("Description (optional)", height=100)
        col1, col2 = st.columns(2)
        urgency = col1.selectbox("Urgency", list(get_theme()['urgency_colors'].keys()))
        tag = col2.selectbox("Tag", [''] + list(TAGS.keys()))
        parent_label = st.text_input("Parent label (blank → current center)")
        edge_type = st.selectbox("Connection Type", list(get_theme()['edge_colors'].keys()))

        if st.form_submit_button("Add") and label:
            pid = None
            if parent_label.strip():
                pid = next((i['id'] for i in get_ideas() if i['label'].strip() == parent_label.strip()), None)
                if pid is None:
                    st.warning("Parent not found; adding as top-level")
            elif get_central() is not None:
                pid = get_central()

            new_node = {
                'id': get_next_id(),
                'label': label.strip(),
                'description': description,
                'urgency': urgency,
                'tag': tag,
                'parent': pid,
                'edge_type': edge_type if pid is not None else 'default',
                'x': None,
                'y': None
            }
            recalc_size(new_node)
            add_idea(new_node)
            increment_next_id()
            st.rerun()

    # Undo/Redo buttons
    undo_col, redo_col = st.sidebar.columns(2)
    if undo_col.button("↩️ Undo", disabled=not can_undo()):
        if perform_undo():
            st.rerun()

    if redo_col.button("↪️ Redo", disabled=not can_redo()):
        if perform_redo():
            st.rerun()

    # Keyboard Shortcuts Info
    with st.sidebar.expander("⌨️ Keyboard Shortcuts"):
        st.markdown("""
        - **Double-click**: Edit node
        - **Right-click**: Delete node
        - **Drag**: Move node
        - **Drag near another**: Change parent
        - **Ctrl+Z**: Undo (when focused on canvas)
        - **Ctrl+Y**: Redo (when focused on canvas)
        - **Ctrl+N**: New node (when focused on canvas)
        """)

    # Edit / Center List
    ideas = get_ideas()
    if ideas:
        # Add custom CSS for better button alignment
        st.markdown("""
        <style>
        div[data-testid="column"] > div > div > div > div > div[data-testid="stButton"] > button {
            width: 100%;
            padding: 0px 5px;
            display: flex;
            justify-content: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.sidebar.expander("✏️ Node List"):
            for node in ideas:
                # More balanced column widths for better alignment
                col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1])
                label_display = node['label']
                if node.get('tag'):
                    label_display = f"[{node['tag']}] {label_display}"
                col1.write(label_display)
                
                # Use smaller emoji icons for better alignment
                if col2.button("🎯", key=f"center_{node['id']}", help="Center this node"):
                    set_central(node['id'])
                    st.rerun()
                
                if col3.button("✏️", key=f"edit_{node['id']}", help="Edit this node"):
                    st.session_state['edit_node'] = node['id']
                    st.rerun()
                
                if col4.button("🗑️", key=f"delete_{node['id']}", help="Delete this node"):
                    save_state_to_history()
                    node_id = node['id']
                    
                    # Get node and all its descendants
                    to_remove = set()
                    
                    def collect_descendants(node_id):
                        to_remove.add(node_id)
                        for child in [n for n in ideas if n.get('parent') == node_id]:
                            collect_descendants(child['id'])
                    
                    collect_descendants(node_id)
                    
                    # Remove collected nodes
                    set_ideas([n for n in ideas if n['id'] not in to_remove])
                    if get_central() in to_remove:
                        set_central(None)
                    st.rerun()  # Force rerun after deletion

    # Node Edit Modal
    if 'edit_node' in st.session_state and st.session_state['edit_node'] is not None:
        node_id = st.session_state['edit_node']
        node = next((n for n in ideas if n['id'] == node_id), None)

        if node:
            with st.form(key=f"edit_node_{node_id}"):
                st.subheader(f"Edit Node: {node['label']}")
                new_label = st.text_input("Label", value=node['label'])
                new_description = st.text_area("Description", value=node.get('description', ''), height=150)
                col1, col2 = st.columns(2)
                new_urgency = col1.selectbox("Urgency",
                                             list(get_theme()['urgency_colors'].keys()),
                                             index=list(get_theme()['urgency_colors'].keys()).index(node.get('urgency', 'low')))
                new_tag = col2.selectbox("Tag",
                                         [''] + list(TAGS.keys()),
                                         index=([''] + list(TAGS.keys())).index(node.get('tag', '')) if node.get('tag', '') in [''] + list(TAGS.keys()) else 0)

                if node['parent'] is not None:
                    parent_node = next((n for n in ideas if n['id'] == node['parent']), None)
                    if parent_node:
                        current_parent = parent_node['label']
                    else:
                        current_parent = ""
                    new_parent = st.text_input("Parent label (blank → no parent)", value=current_parent)
                    new_edge_type = st.selectbox("Connection Type",
                                                 list(get_theme()['edge_colors'].keys()),
                                                 index=list(get_theme()['edge_colors'].keys()).index(node.get('edge_type', 'default')))
                else:
                    new_parent = st.text_input("Parent label (blank → no parent)")
                    new_edge_type = st.selectbox("Connection Type", list(get_theme()['edge_colors'].keys()))

                col1, col2 = st.columns(2)
                if col1.form_submit_button("Save Changes"):
                    save_state_to_history()
                    node['label'] = new_label
                    node['description'] = new_description
                    node['urgency'] = new_urgency
                    node['tag'] = new_tag
                    recalc_size(node)

                    # Update parent if needed
                    if new_parent.strip():
                        new_pid = next((i['id'] for i in get_ideas() if i['label'].strip() == new_parent.strip()), None)
                        if new_pid is not None and new_pid != node['id']:  # Prevent self-reference
                            from src.handlers import is_circular
                            if not is_circular(node['id'], new_pid, ideas):
                                node['parent'] = new_pid
                                node['edge_type'] = new_edge_type
                            else:
                                st.warning("Cannot create circular parent-child relationships")
                        elif new_pid == node['id']:
                            st.warning("Cannot set a node as its own parent.")
                    else:
                        node['parent'] = None
                        node['edge_type'] = 'default'

                    st.session_state['edit_node'] = None
                    st.rerun()

                if col2.form_submit_button("Cancel"):
                    st.session_state['edit_node'] = None
                    st.rerun()

    # Tutorial Prompt When Empty
    if not ideas:
        st.info("Your map is empty! Use the Add Bubble form on the left to get started.")
        with st.expander("Quick Tutorial"):
            st.markdown("""
            ### Getting Started with Enhanced Mind Map

            1. **Add your first bubble** using the form on the left sidebar
            2. **Organize your ideas** by creating parent-child relationships
            3. **Use tags** to categorize different types of nodes
            4. **Set urgency levels** to visually prioritize important ideas
            5. **Add descriptions** to provide more context for each node
            6. **Customize connection types** to show different relationships
            7. **Use the theme selector** to change the visual appearance

            **Interactive Features:**
            - Double-click a node to edit it
            - Right-click a node to delete it
            - Drag nodes to reposition them
            - Drag a node close to another to change its parent
            - Use undo/redo buttons to reverse changes
            """)
        st.stop()

    # Build PyVis Network
    theme = get_theme()
    net = Network(height="650px", width="100%", directed=True, bgcolor=theme['background'])

    # Configure physics for better node placement and shorter connections
    net.barnes_hut(
        gravity=-2000,     # Less negative value reduces repulsion
        central_gravity=0.3,  # Higher value keeps nodes more centered
        spring_length=50,   # Shorter spring length for connections
        spring_strength=spring_strength,  # Stronger springs pulls connected nodes closer
        damping=0.09,       # Slightly increased damping
        overlap=0          # Prevent node overlap
    )

    id_set = {n['id'] for n in ideas}
    for n in ideas:
        recalc_size(n)

        # Set color based on tag first, then urgency
        if n.get('tag') and n['tag'] in TAGS:
            color_hex = get_tag_color(n['tag'])
        else:
            color_hex = get_urgency_color(n['urgency'])

        r, g, b = hex_to_rgb(color_hex)
        bg, bd = f"rgba({r},{g},{b},{RGBA_ALPHA})", f"rgba({r},{g},{b},1)"

        # Apply the size multiplier to make urgency differences more noticeable
        base_size = n['size']
        if n.get('urgency') == 'high':
            base_size = base_size * size_multiplier
        elif n.get('urgency') == 'low':
            base_size = base_size / size_multiplier
            
        size_px = base_size * (1.5 if n['id'] == get_central() else 1)

        # Prepare node title with description for hover text
        title = n['label']
        if n.get('tag'):
            title = f"[{n['tag']}] {title}"
        if n.get('description'):
            title += f"\n\n{n['description']}"

        kwargs = {
            'label': n['label'],
            'title': title,
            'size': size_px,
            'color': {'background': bg, 'border': bd},
            'borderWidth': PRIMARY_NODE_BORDER if n['id'] == get_central() else 1,
            'shape': 'circle',
            'fixed': {'x': False, 'y': False}
        }

        if n['x'] is not None and n['y'] is not None:
            kwargs.update(x=n['x'], y=n['y'])

        net.add_node(n['id'], **kwargs)

    for n in ideas:
        pid = n.get('parent')
        if pid in id_set:
            edge_type = n.get('edge_type', 'default')
            edge_color = get_edge_color(edge_type)
            net.add_edge(pid, n['id'], arrows='to', color=edge_color, title=edge_type, length=edge_length)

    # JavaScript for interactions - IMPROVED with URL param messaging and error handling
    js = textwrap.dedent(f"""
    const nodes = network.body.data.nodes;
    const edges = network.body.data.edges;
    const highlight = '{search_q.lower()}';

    // URL parameter-based messaging
    function send(action, payload) {{
        try {{
            const data = JSON.stringify({{type: action, payload: payload}});
            // Use URL parameters for communication
            const url = new URL(window.location.href);
            url.searchParams.set('msg', data);
            window.location.href = url.toString();
        }} catch (error) {{
            console.error("Failed to send message:", error);
        }}
    }}

    // Initialize physics to apply once then stabilize
    network.once('afterDrawing', () => {{
        try {{
            network.stabilize(100);  // Stabilize for better initial layout
            setTimeout(() => network.physics.stabilize(), 1000); // Additional stabilization
            setTimeout(() => network.physics.disable(), 2000); // Then disable physics
        }} catch (error) {{
            console.error("Physics initialization error:", error);
        }}
    }});

    // Handle node dragging
    network.on('dragEnd', params => {{
        try {{
            const pos = network.getPositions(); 
            send('pos', pos);
            
            // Improved reparenting detection with better threshold
            if (params.nodes.length === 1) {{
                const id = params.nodes[0]; 
                const p = pos[id];
                const others = Object.entries(pos)
                    .filter(([nodeId, _]) => parseInt(nodeId) !== id)
                    .map(([nodeId, pos]) => {{ 
                        return {{ 
                            id: parseInt(nodeId), 
                            dist: Math.hypot(p.x - pos.x, p.y - pos.y) 
                        }}; 
                    }})
                    .sort((a, b) => a.dist - b.dist);
                
                if (others.length && others[0].dist < 100) {{
                    send('reparent', {{ id, parent: others[0].id }});
                }}
            }}
        }} catch (error) {{
            console.error("Error in dragEnd handler:", error);
        }}
    }});

    // Handle double-click for edit
    network.on('doubleClick', params => {{
        try {{
            if (params.nodes.length === 1) {{
                const id = params.nodes[0];
                send('edit_modal', {{ id }});
            }}
        }} catch (error) {{
            console.error("Error in doubleClick handler:", error);
        }}
    }});

    // Improved right-click delete
    network.on('oncontext', params => {{
        try {{
            params.event.preventDefault();  // Prevent default context menu
            if (params.nodes.length === 1) {{
                const id = parseInt(params.nodes[0]);
                if (confirm('Delete this bubble?')) {{
                    send('delete', {{ id }});
                }}
            }}
        }} catch (error) {{
            console.error("Error in oncontext handler:", error);
        }}
    }});

    // Improved keyboard shortcuts with better focus handling
    document.addEventListener('keydown', (e) => {{
        try {{
            // Get the network container
            const networkDiv = document.getElementById('mynetwork');
            
            // Only process if focus is on the document body or network canvas
            const focused = document.activeElement === document.body || 
                          networkDiv.contains(document.activeElement) ||
                          document.activeElement.tagName === 'BODY';
            
            if (focused) {{
                // Ctrl+Z for undo
                if ((e.ctrlKey || e.metaKey) && e.key === 'z') {{
                    e.preventDefault();
                    send('undo', {{}});
                }}
                // Ctrl+Y for redo
                else if ((e.ctrlKey || e.metaKey) && e.key === 'y') {{
                    e.preventDefault();
                    send('redo', {{}});
                }}
                // Ctrl+N for new node
                else if ((e.ctrlKey || e.metaKey) && e.key === 'n') {{
                    e.preventDefault();
                    const label = prompt('New node label:');
                    if (label && label.trim()) {{
                        send('new_node', {{ label }});
                    }}
                }}
            }}
        }} catch (error) {{
            console.error("Error in keyboard handler:", error);
        }}
    }});

    // Search highlight
    if (highlight) {{
        try {{
            nodes.get().forEach(n => {{
                if (n.label.toLowerCase().includes(highlight.toLowerCase()) || 
                    (n.title && n.title.toLowerCase().includes(highlight.toLowerCase()))) {{
                    nodes.update({{ id: n.id, color: {{ background: 'yellow', border: 'orange' }} }});
                }}
            }});
        }} catch (error) {{
            console.error("Error in search highlighting:", error);
        }}
    }}
""")

    html = net.generate_html() + f"<script>{js}</script>"
    components.html(html, height=650)

    # Check query parameters for messages from JavaScript
    if 'msg' in st.query_params:
        try:
            msg_str = st.query_params.get('msg')
            if msg_str:
                msg_data = json.loads(msg_str)
                handle_message(msg_data)
                # Clear message from URL to prevent reprocessing
                st.query_params.pop('msg')
        except Exception as e:
            handle_exception(e)

    # Node details section when a central node is selected
    if get_central() is not None:
        central_node = next((n for n in ideas if n['id'] == get_central()), None)
        if central_node:
            st.subheader(f"📌 Selected: {central_node['label']}")

            # Display node details
            if central_node.get('tag'):
                st.write(f"**Tag:** {central_node['tag']}")

            st.write(f"**Urgency:** {central_node['urgency']}")

            if central_node.get('description'):
                st.markdown("**Description:**")
                st.markdown(central_node['description'])

            # Display children
            children = [n for n in ideas if n.get('parent') == central_node['id']]
            if children:
                st.markdown("**Connected Ideas:**")
                for child in children:
                    st.markdown(f"- {child['label']} ({child.get('edge_type', 'default')} connection)")

except Exception as e:
    handle_exception(e)