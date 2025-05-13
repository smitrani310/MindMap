"""
Position Export Check Script

This script inspects the exported JSON file to verify positions are correctly saved.
"""

import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger('position_export_check')

# Add the parent directory to the path to import project modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

def find_data_file():
    """Find the mind map data file"""
    data_file = os.path.join(parent_dir, 'mindmap_data.json')
    if os.path.exists(data_file):
        return data_file
    
    # Try alternate locations
    alternates = [
        'data.json',
        'mindmap_export.json',
        os.path.join(parent_dir, 'data', 'mindmap_data.json')
    ]
    
    for alt in alternates:
        if os.path.exists(alt):
            return alt
    
    return None

def analyze_positions(file_path):
    """Analyze node positions in the data file"""
    try:
        # Load the file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check if it's a direct list (export format) or has ideas key (data store format)
        if isinstance(data, list):
            nodes = data
        elif isinstance(data, dict) and 'ideas' in data:
            nodes = data['ideas']
        else:
            logger.error(f"Unexpected data format in {file_path}")
            return False
        
        # Count nodes
        total_nodes = len(nodes)
        logger.info(f"Found {total_nodes} nodes in {file_path}")
        
        # Count nodes with default positions
        default_positions = sum(1 for n in nodes if n.get('x') == 0 and n.get('y') == 0)
        logger.info(f"Nodes with (0,0) position: {default_positions} ({default_positions/total_nodes*100:.1f}%)")
        
        # Count nodes with non-default positions
        non_default = sum(1 for n in nodes if n.get('x') != 0 or n.get('y') != 0)
        logger.info(f"Nodes with non-zero positions: {non_default} ({non_default/total_nodes*100:.1f}%)")
        
        # Check for nodes without position data
        missing_positions = sum(1 for n in nodes if 'x' not in n or 'y' not in n)
        logger.info(f"Nodes missing position data: {missing_positions}")
        
        # Log the positions of all nodes
        logger.info("Node positions:")
        for node in nodes:
            node_id = node.get('id', 'unknown')
            label = node.get('label', 'Untitled')
            pos_x = node.get('x', 'missing')
            pos_y = node.get('y', 'missing')
            logger.info(f"  - Node {node_id} '{label}': ({pos_x}, {pos_y})")
        
        return True
    except Exception as e:
        logger.error(f"Error analyzing positions: {str(e)}")
        return False

def check_export_process():
    """Test exporting and verify positions are kept"""
    try:
        # Import the necessary functions
        try:
            from src.state import get_store, save_data
            HAS_IMPORTS = True
        except ImportError:
            logger.warning("Could not import state functions, simple file check only")
            HAS_IMPORTS = False
        
        # First check the main data file
        data_file = find_data_file()
        if data_file:
            logger.info(f"Checking main data file: {data_file}")
            analyze_positions(data_file)
        else:
            logger.warning("Main data file not found")
        
        # If imports available, test actual export
        if HAS_IMPORTS:
            from src.state import get_store
            
            # Get current store
            store = get_store()
            ideas = store.get('ideas', [])
            
            # Create export data
            export = [item.copy() for item in ideas]
            for item in export:
                # Add is_central flag
                item['is_central'] = (item.get('id') == store.get('central'))
            
            # Save to temporary export file
            export_file = os.path.join(parent_dir, 'test_export.json')
            with open(export_file, 'w') as f:
                json.dump(export, f, indent=2)
            
            logger.info(f"Created test export file: {export_file}")
            
            # Analyze the export
            logger.info("Analyzing export file:")
            analyze_positions(export_file)
            
            return True
    except Exception as e:
        logger.error(f"Error testing export: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n========== Node Position Export Check ==========\n")
    
    # Check the export process
    result = check_export_process()
    
    print("\n==============================================\n")
    if result:
        print("✅ Export check completed")
    else:
        print("❌ Export check failed") 