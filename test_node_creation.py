#!/usr/bin/env python3
"""Test script to verify node creation functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.integration.service_adapter import get_service_adapter

def test_node_creation():
    """Test node creation through the service adapter."""
    try:
        print("Initializing service adapter...")
        adapter = get_service_adapter()
        print("✓ Service adapter initialized successfully")
        
        print(f"Current nodes: {len(adapter.get_ideas())}")
        
        # Test adding a node
        test_node = {
            'label': 'Test Node',
            'description': 'Test description',
            'urgency': 'medium',
            'tag': 'test',
            'parent': None,
            'edge_type': 'default',
            'x': 100,
            'y': 100
        }
        
        print("Adding test node...")
        result = adapter.add_idea(test_node)
        print(f"Add node result: {result}")
        
        if result:
            print("✓ Node added successfully!")
            print(f"Nodes after adding: {len(adapter.get_ideas())}")
            
            # Get the added node
            ideas = adapter.get_ideas()
            if ideas:
                latest_node = ideas[-1]
                print(f"Latest node: {latest_node['label']} (ID: {latest_node['id']})")
            
        else:
            print("✗ Failed to add node")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_node_creation()