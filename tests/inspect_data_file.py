"""
Inspect Data File

This script inspects the mind map data file to check if node positions are being saved correctly.
"""

import os
import sys
import json
import logging
import argparse
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger('inspect_data')

def find_data_file(data_dir=None):
    """Find the mind map data file"""
    # Default search locations
    search_paths = [
        '.',  # Current directory
        './data',  # Data directory
        '../data',  # Parent data directory
    ]
    
    # Add custom directory if provided
    if data_dir:
        search_paths.insert(0, data_dir)
        
    # Common data file names
    data_files = [
        'mindmap_data.json',
        'mind_map_data.json',
        'data.json'
    ]
    
    # Search for data files
    for path in search_paths:
        for filename in data_files:
            filepath = os.path.join(path, filename)
            if os.path.exists(filepath):
                logger.info(f"Found data file: {filepath}")
                return filepath
    
    logger.error("No data file found!")
    return None

def load_data(filepath):
    """Load data from a JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading data: {e}")
        return None

def analyze_data(data):
    """Analyze node data for position information"""
    if not data or not isinstance(data, dict):
        logger.error("Invalid data format!")
        return
    
    # Check if data has an 'ideas' key
    if 'ideas' not in data:
        logger.error("No 'ideas' key found in data!")
        return
    
    ideas = data['ideas']
    if not isinstance(ideas, list):
        logger.error("'ideas' is not a list!")
        return
    
    logger.info(f"Found {len(ideas)} nodes in the data file")
    
    # Check for position data
    nodes_with_position = []
    nodes_without_position = []
    position_stats = defaultdict(int)
    
    for node in ideas:
        # Check if node has position data
        has_x = 'x' in node
        has_y = 'y' in node
        
        # Track stats
        if has_x and has_y:
            nodes_with_position.append(node)
            position_stats['both_coords'] += 1
            
            # Check for reasonable values
            if node['x'] == 0 and node['y'] == 0:
                position_stats['zero_position'] += 1
            elif -10 <= node['x'] <= 10 and -10 <= node['y'] <= 10:
                position_stats['near_origin'] += 1
            else:
                position_stats['positioned'] += 1
        elif has_x or has_y:
            nodes_without_position.append(node)
            position_stats['missing_coord'] += 1
        else:
            nodes_without_position.append(node)
            position_stats['no_coords'] += 1
    
    # Report findings
    logger.info(f"Position data analysis:")
    logger.info(f"  Nodes with position data: {len(nodes_with_position)} ({len(nodes_with_position)/len(ideas)*100:.1f}%)")
    logger.info(f"  Nodes without position data: {len(nodes_without_position)} ({len(nodes_without_position)/len(ideas)*100:.1f}%)")
    
    logger.info(f"Position statistics:")
    logger.info(f"  Nodes with both x and y: {position_stats['both_coords']}")
    logger.info(f"  Nodes with (0,0) position: {position_stats['zero_position']}")
    logger.info(f"  Nodes near origin: {position_stats['near_origin']}")
    logger.info(f"  Nodes with significant position: {position_stats['positioned']}")
    logger.info(f"  Nodes with missing coordinate: {position_stats['missing_coord']}")
    logger.info(f"  Nodes with no coordinates: {position_stats['no_coords']}")
    
    # Check for suspicious patterns
    if position_stats['zero_position'] > 0.8 * len(ideas):
        logger.warning("⚠️ Most nodes have (0,0) position - positions might not be saved correctly!")
    
    # Return detailed data for further inspection
    return {
        'total_nodes': len(ideas),
        'with_position': len(nodes_with_position),
        'without_position': len(nodes_without_position),
        'stats': position_stats,
        'sample_with_position': nodes_with_position[:5] if nodes_with_position else None,
        'sample_without_position': nodes_without_position[:5] if nodes_without_position else None,
    }

def inspect_position_updates(data, node_id=None):
    """Look for evidence of position updates in the data"""
    if not data or 'ideas' not in data:
        return
    
    ideas = data['ideas']
    
    # If node_id specified, focus on that node
    if node_id:
        # Find the node
        node = next((n for n in ideas if n.get('id') == node_id), None)
        if not node:
            logger.error(f"Node with ID {node_id} not found!")
            return
        
        logger.info(f"Inspecting node {node_id}:")
        if 'x' in node and 'y' in node:
            logger.info(f"  Position: ({node['x']}, {node['y']})")
        else:
            logger.info(f"  No position data found!")
        
        # Show all data for the node
        logger.info(f"  All data: {json.dumps(node, indent=2)}")
        return
    
    # No specific node - look for patterns
    # Check for variety in positions - if positions are being saved,
    # we'd expect to see a variety of positions
    x_values = set()
    y_values = set()
    
    for node in ideas:
        if 'x' in node:
            x_values.add(node['x'])
        if 'y' in node:
            y_values.add(node['y'])
    
    logger.info(f"Position variety:")
    logger.info(f"  Unique X values: {len(x_values)}")
    logger.info(f"  Unique Y values: {len(y_values)}")
    
    # If there's only one value (especially 0), that's suspicious
    if len(x_values) <= 1 or len(y_values) <= 1:
        logger.warning("⚠️ Very little variation in positions - positions might not be updating!")
    
    # Show top 5 nodes with non-zero positions
    interesting_nodes = [
        n for n in ideas 
        if 'x' in n and 'y' in n and (n['x'] != 0 or n['y'] != 0)
    ]
    
    if interesting_nodes:
        logger.info(f"Sample nodes with non-zero positions:")
        for i, node in enumerate(interesting_nodes[:5]):
            logger.info(f"  Node {i+1}: id={node.get('id')}, pos=({node.get('x')}, {node.get('y')}), label=\"{node.get('label', '')}\"")
    else:
        logger.warning("⚠️ No nodes with non-zero positions found!")

def check_visualization_code():
    """Look for vis.js code that positions nodes"""
    # Common locations for visualization code
    vis_file_paths = [
        'main.py',
        'src/network_handlers.js',
        'src/visualization.js',
        'src/graph.js'
    ]
    
    found_code = False
    
    for path in vis_file_paths:
        if not os.path.exists(path):
            continue
        
        try:
            with open(path, 'r') as f:
                content = f.read()
                
            logger.info(f"Examining {path} for visualization code")
            
            # Look for vis.js position-related code
            if 'getPositions' in content:
                logger.info(f"  Found 'getPositions' method in {path}")
                found_code = True
                
            if 'dragEnd' in content:
                logger.info(f"  Found 'dragEnd' event in {path}")
                found_code = True
                
            if 'position' in content and 'x' in content and 'y' in content:
                logger.info(f"  Found position coordinates reference in {path}")
                found_code = True
                
            # Look for Python code that handles positions
            if 'pos' in content and '_handle_position' in content:
                logger.info(f"  Found position handler in {path}")
                found_code = True
        except IOError as e:
            logger.error(f"Error reading {path}: {e}")
    
    if not found_code:
        logger.warning("⚠️ No position-related code found in common files!")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Inspect mind map data file for position information")
    parser.add_argument("--dir", help="Directory to search for data file")
    parser.add_argument("--file", help="Specific data file to inspect")
    parser.add_argument("--node", type=int, help="Specific node ID to inspect")
    parser.add_argument("--check-code", action="store_true", help="Check visualization code for position handling")
    args = parser.parse_args()
    
    # Find and load data file
    if args.file:
        filepath = args.file
    else:
        filepath = find_data_file(args.dir)
    
    if not filepath:
        logger.error("No data file found. Use --dir or --file to specify location.")
        return 1
    
    data = load_data(filepath)
    if not data:
        return 1
    
    # Analyze the data
    result = analyze_data(data)
    
    # Inspect position updates
    inspect_position_updates(data, args.node)
    
    # Check visualization code if requested
    if args.check_code:
        check_visualization_code()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 