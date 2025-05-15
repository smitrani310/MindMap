"""
Network visualization module for the Mind Map application.

This module handles:
- PyVis Network creation and configuration
- Node styling and coloring
- Edge creation and styling
- HTML generation and JavaScript integration
"""

import json
import logging
from typing import Dict, Any, List, Set
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

from src.config import (
    DEFAULT_SETTINGS, NETWORK_CONFIG,
    RGBA_ALPHA, PRIMARY_NODE_BORDER
)
from src.state import get_store, get_ideas, get_central
from src.utils import (
    hex_to_rgb, get_theme, recalc_size, 
    get_edge_color, get_urgency_color, get_tag_color
)

# Get logger
logger = logging.getLogger(__name__)

def render_network_visualization(canvas_height: str) -> None:
    """
    Render the network visualization using PyVis.
    
    Args:
        canvas_height: The height of the canvas (e.g., "600px")
    """
    # Build PyVis Network
    theme = get_theme()
    
    # Create network with transparent background for seamless integration
    net = Network(
        height=canvas_height, 
        width="100%", 
        directed=True, 
        bgcolor=theme['background'],
        font_color=theme.get('text_color', '#333333'),
        select_menu=False,  # Remove the default right-click menu
        filter_menu=False,  # Remove the filter menu
        cdn_resources='local'  # Use local resources for better loading
    )

    # Configure physics using centralized settings
    net.barnes_hut(
        gravity=NETWORK_CONFIG['gravity'],
        central_gravity=NETWORK_CONFIG['central_gravity'],
        spring_length=NETWORK_CONFIG['spring_length'],
        spring_strength=get_store().get('settings', {}).get('spring_strength', DEFAULT_SETTINGS['spring_strength']),
        damping=NETWORK_CONFIG['damping'],
        overlap=NETWORK_CONFIG['overlap']
    )

    # Build nodes and edges
    build_nodes_and_edges(net)
    
    # Generate and enhance HTML
    modified_html = enhance_network_html(net.generate_html())
    
    # Add node position data to HTML
    modified_html = add_position_data_to_html(modified_html)
    
    # Add JavaScript utilities
    modified_html = add_javascript_utilities(modified_html)

    # Render the modified HTML
    components.html(
        modified_html, 
        height=int(canvas_height.replace("px", "")), 
        scrolling=False
    )

def build_nodes_and_edges(net: Network) -> None:
    """
    Build nodes and edges for the network.
    
    Args:
        net: The PyVis Network object
    """
    # Add nodes and edges to the network
    id_set = {n['id'] for n in get_ideas() if 'id' in n}
    
    # Get central node
    central_id = get_central()
    logger.info(f"Creating nodes with central node ID: {central_id}")
    
    # Add all nodes
    add_nodes_to_network(net, central_id)
    
    # Add all edges
    add_edges_to_network(net, id_set)

def add_nodes_to_network(net: Network, central_id: int) -> None:
    """
    Add nodes to the network with appropriate styling.
    
    Args:
        net: The PyVis Network object
        central_id: The ID of the central node
    """
    for n in get_ideas():
        # Skip nodes without an id
        if 'id' not in n:
            continue
            
        recalc_size(n)

        # Get the color mode from settings
        color_mode = get_store().get('settings', {}).get('color_mode', 'urgency')
        
        # Log node and coloring details
        node_id = n.get('id')
        node_tag = n.get('tag', '')
        node_urgency = n.get('urgency', 'medium')
        logger.debug(f"Coloring node {node_id} with tag='{node_tag}', urgency='{node_urgency}', mode='{color_mode}'")
        
        # Set color based on tag or urgency depending on color mode
        if color_mode == 'tag' and n.get('tag'):
            # Use tag color if available
            color_hex = get_tag_color(n['tag'])
            logger.debug(f"Node {node_id}: Using tag color {color_hex} for tag '{n['tag']}'")
        else:
            # Fall back to urgency color
            color_hex = get_urgency_color(n.get('urgency', 'medium'))
            logger.debug(f"Node {node_id}: Using urgency color {color_hex} for '{n.get('urgency', 'medium')}'")

        r, g, b = hex_to_rgb(color_hex)
        bg, bd = f"rgba({r},{g},{b},{RGBA_ALPHA})", f"rgba({r},{g},{b},1)"

        # Apply the size multiplier to make urgency differences more noticeable
        base_size = n.get('size', 20)  # Default size of 20 if not set
        size_multiplier = get_store().get('settings', {}).get('size_multiplier', DEFAULT_SETTINGS['size_multiplier'])
        if n.get('urgency') == 'high':
            base_size = base_size * size_multiplier
        elif n.get('urgency') == 'low':
            base_size = base_size / size_multiplier
            
        size_px = base_size * (1.5 if n['id'] == central_id else 1)
        
        # Apply special highlighting for central node
        is_central = n['id'] == central_id
        if is_central:
            bd = "#FF5722"  # Bright orange border
            border_width = 3  # Thicker border
            logger.info(f"Applying special highlighting to central node {n['id']}")
        else:
            border_width = 1

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
            'borderWidth': border_width,
            'shape': 'circle',
            'fixed': {'x': False, 'y': False}
        }

        if n['x'] is not None and n['y'] is not None:
            kwargs.update(x=n['x'], y=n['y'])

        net.add_node(n['id'], **kwargs)

def add_edges_to_network(net: Network, id_set: Set[int]) -> None:
    """
    Add edges to the network.
    
    Args:
        net: The PyVis Network object
        id_set: Set of valid node IDs
    """
    for n in get_ideas():
        # Skip nodes without an id
        if 'id' not in n:
            continue
            
        pid = n.get('parent')
        if pid in id_set:
            edge_type = n.get('edge_type', 'default')
            # Make sure the edge type is valid for the current theme
            if edge_type not in get_theme()['edge_colors']:
                edge_type = 'default'  # Fallback to default if not in theme
            edge_color = get_edge_color(edge_type)
            edge_length = get_store().get('settings', {}).get('edge_length', DEFAULT_SETTINGS['edge_length'])
            net.add_edge(pid, n['id'], arrows='to', color=edge_color, title=edge_type, length=edge_length)

def enhance_network_html(html_content: str) -> str:
    """
    Enhance the PyVis HTML with additional features.
    
    Args:
        html_content: The original HTML content
        
    Returns:
        Enhanced HTML content
    """
    # Create simplified HTML with direct network object access
    modified_html = html_content.replace(
        'var network = new vis.Network(',
        'window.visNetwork = new vis.Network('
    )
    
    # Add additional hook to ensure network is accessible globally
    modified_html = modified_html.replace(
        '</script>',
        '''
        // Add hook to ensure visNetwork is available
        if (typeof network !== 'undefined' && !window.visNetwork) {
            console.log('Setting window.visNetwork from local network variable');
            window.visNetwork = network;
        }
        
        // Debug that will run after network creation
        setTimeout(function() {
            console.log('Network object availability check:');
            console.log('- window.visNetwork available:', window.visNetwork !== undefined);
            if (!window.visNetwork) {
                console.log('Searching for network in canvases...');
                var networkDiv = document.getElementById('mynetwork');
                if (networkDiv) {
                    var canvases = networkDiv.querySelectorAll('canvas');
                    for (var i = 0; i < canvases.length; i++) {
                        if (canvases[i].network) {
                            console.log('Found network object in canvas');
                            window.visNetwork = canvases[i].network;
                            break;
                        }
                    }
                }
            }
        }, 1000);
        </script>'''
    )

    # Add direct event listeners to guarantee they are attached
    # Load the JavaScript files from the extracted modules instead of inline code
    js_files = [
        'src/js/message_relay.js',
        'src/js/position_tracking.js',
        'src/js/network_events.js'
    ]
    
    # Read the JS files and combine them into a single script element
    js_files_content = ""
    for js_file in js_files:
        try:
            with open(js_file, 'r') as f:
                js_files_content += f.read() + "\n\n"
        except Exception as e:
            logger.error(f"Error loading JS file {js_file}: {str(e)}")
    
    direct_js = f"""
    <script>
    {js_files_content}
    </script>
    """

    # Add the direct JS right before the closing </body> tag
    modified_html = modified_html.replace('</body>', direct_js + '</body>')
    
    return modified_html

def add_position_data_to_html(html_content: str) -> str:
    """
    Add position data to the HTML.
    
    Args:
        html_content: The HTML content
        
    Returns:
        HTML content with position data
    """
    # Get network positions for all nodes
    node_positions = {}
    for n in get_ideas():
        if 'id' in n and 'x' in n and 'y' in n and n['x'] is not None and n['y'] is not None:
            node_id = n['id']
            x = n['x']
            y = n['y']
            # Skip (0,0) positions that might be default
            if float(x) != 0.0 or float(y) != 0.0:
                node_positions[node_id] = {'x': float(x), 'y': float(y)}
    
    # Insert the position data into the JavaScript
    position_data_js = f"""
    <script>
    // Initialize position data from server
    window.serverNodePositions = {json.dumps(node_positions)};
    
    console.log('📊 Loaded position data for', Object.keys(window.serverNodePositions).length, 'nodes from server');
    </script>
    """
    
    # Add position data initialization to the HTML
    return html_content + position_data_js

def add_javascript_utilities(html_content: str) -> str:
    """
    Add JavaScript utilities to the HTML.
    
    Args:
        html_content: The HTML content
        
    Returns:
        HTML content with JavaScript utilities
    """
    # Include our custom utils.js file to fix the Streamlit namespace error
    try:
        with open("src/utils.js", "r") as f:
            utils_js = f.read()
            utils_js_html = f"""
            <script type="text/javascript">
            // Immediately define Streamlit namespace to prevent errors
            if (typeof window.Streamlit === 'undefined') {{
                window.Streamlit = {{ 
                    setComponentValue: function() {{ console.log('Streamlit mock: setComponentValue called'); }},
                    setComponentReady: function() {{ console.log('Streamlit mock: setComponentReady called'); }},
                    receiveMessageFromPython: function() {{ console.log('Streamlit mock: receiveMessageFromPython called'); }}
                }};
                console.log('Created Streamlit namespace mock to prevent errors');
            }}
            </script>
            <script type="text/javascript">
            {utils_js}
            </script>
            """
        
        # Add utils.js to the HTML
        return html_content + utils_js_html
    except Exception as e:
        logger.error(f"Error loading utils.js: {str(e)}")
        return html_content 