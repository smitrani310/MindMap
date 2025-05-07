"""Utilities for node validation and manipulation."""

def validate_node(node, get_next_id_func, increment_next_id_func):
    """Validate and fix node structure to ensure all required fields are present.
    
    Args:
        node: Node dictionary to validate
        get_next_id_func: Function to get the next available node ID
        increment_next_id_func: Function to increment the next ID counter
        
    Returns:
        Validated and fixed node dictionary
    """
    # Ensure node is a dictionary
    if not isinstance(node, dict):
        # Create a minimal valid node if the input is invalid
        return {
            'id': get_next_id_func(),
            'label': 'Fixed Node',
            'parent': None,
            'description': '',
            'urgency': 'medium',
            'tag': '',
            'edge_type': 'default',
            'x': None,
            'y': None
        }
    
    # Check and add required fields if missing
    if 'id' not in node:
        node['id'] = get_next_id_func()
        increment_next_id_func()
        
    node.setdefault('label', 'Untitled Node')
    node.setdefault('parent', None)
    node.setdefault('description', '')
    node.setdefault('urgency', 'medium')
    node.setdefault('tag', '')
    node.setdefault('edge_type', 'default')
    node.setdefault('x', None)
    node.setdefault('y', None)
    
    # Ensure the id is an integer
    if not isinstance(node['id'], int):
        try:
            node['id'] = int(node['id'])
        except (ValueError, TypeError):
            node['id'] = get_next_id_func()
            increment_next_id_func()
    
    return node 