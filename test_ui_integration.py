#!/usr/bin/env python3
"""Test script to verify UI integration with service adapter."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock streamlit session state for testing
class MockSessionState:
    def __init__(self):
        self._state = {}
    
    def __getitem__(self, key):
        return self._state.get(key)
    
    def __setitem__(self, key, value):
        self._state[key] = value
    
    def __contains__(self, key):
        return key in self._state
    
    def get(self, key, default=None):
        return self._state.get(key, default)
    
    def pop(self, key, default=None):
        return self._state.pop(key, default)

# Mock streamlit module
class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()

# Set up mock
import streamlit as st
mock_st = MockStreamlit()
sys.modules['streamlit'].session_state = mock_st.session_state

def test_service_adapter_integration():
    """Test the service adapter integration."""
    try:
        print("=== Testing Service Adapter Integration ===")
        
        from src.integration.service_adapter import get_service_adapter
        
        print("1. Initializing service adapter...")
        adapter = get_service_adapter()
        print("✓ Service adapter initialized")
        
        print(f"2. Current nodes: {len(adapter.get_ideas())}")
        
        print("3. Testing node creation...")
        test_node = {
            'label': 'UI Integration Test',
            'description': 'Testing UI integration',
            'urgency': 'high',
            'tag': 'test',
            'parent': None,
            'edge_type': 'default',
            'x': 200,
            'y': 200
        }
        
        result = adapter.add_idea(test_node)
        print(f"   Add result: {result}")
        
        if result:
            print("✓ Node creation successful")
            ideas = adapter.get_ideas()
            print(f"   Total nodes now: {len(ideas)}")
            
            # Find our test node
            test_nodes = [n for n in ideas if n['label'] == 'UI Integration Test']
            if test_nodes:
                node = test_nodes[0]
                print(f"   Created node: ID={node['id']}, Label='{node['label']}'")
                print(f"   Urgency: {node['urgency']}, Tag: {node['tag']}")
            
        else:
            print("✗ Node creation failed")
            return False
        
        print("4. Testing node search...")
        search_results = adapter.search_nodes("Integration")
        print(f"   Search results: {len(search_results)} nodes found")
        
        print("5. Testing statistics...")
        stats = adapter.get_statistics()
        print(f"   Total nodes: {stats.get('total_nodes', 0)}")
        print(f"   Urgency distribution: {stats.get('urgency_distribution', {})}")
        
        print("6. Testing central node operations...")
        central = adapter.get_central()
        print(f"   Current central node: {central}")
        
        # Test setting central node
        if len(adapter.get_ideas()) > 0:
            first_node_id = adapter.get_ideas()[0]['id']
            result = adapter.set_central(first_node_id)
            print(f"   Set central node result: {result}")
            
            new_central = adapter.get_central()
            print(f"   New central node: {new_central}")
        
        print("\n✅ All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test backward compatibility functions."""
    try:
        print("\n=== Testing Backward Compatibility ===")
        
        from src.integration.service_adapter import get_ideas, add_idea, get_central, set_central
        
        print("1. Testing backward compatibility functions...")
        
        # Test get_ideas
        ideas = get_ideas()
        print(f"   get_ideas(): {len(ideas)} nodes")
        
        # Test get_central
        central = get_central()
        print(f"   get_central(): {central}")
        
        # Test add_idea
        compat_node = {
            'label': 'Compatibility Test',
            'description': 'Testing backward compatibility',
            'urgency': 'medium',
            'tag': 'compat',
            'parent': None,
            'edge_type': 'default',
            'x': 300,
            'y': 300
        }
        
        result = add_idea(compat_node)
        print(f"   add_idea() result: {result}")
        
        if result:
            new_ideas = get_ideas()
            print(f"   Nodes after adding: {len(new_ideas)}")
        
        print("✅ Backward compatibility tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Backward compatibility test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_service_adapter_integration()
    success2 = test_backward_compatibility()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Node creation functionality is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")