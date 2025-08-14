#!/usr/bin/env python3
"""
Test script for the new main application.

This script tests the new architecture integration without running the full Streamlit app.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.integration.service_adapter import ServiceAdapter
from src.infrastructure.config import AppConfig


def test_service_adapter_basic_functionality():
    """Test basic functionality of the service adapter."""
    print("Testing Service Adapter Basic Functionality...")
    
    # Create temporary configuration
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = AppConfig(
            data_file=str(temp_path / "test_main.json"),
            backup_dir=str(temp_path / "backups"),
            log_dir=str(temp_path / "logs"),
            environment="testing"
        )
        
        # Create service adapter with temporary config
        from unittest.mock import patch
        with patch('src.integration.service_adapter.ConfigFactory.create_config', return_value=config):
            adapter = ServiceAdapter()
        
        # Test 1: Add a node
        print("  - Testing node creation...")
        node_data = {
            'label': 'Test Node',
            'description': 'Testing the new architecture',
            'x': 100,
            'y': 200,
            'urgency': 'high',
            'tag': 'test'
        }
        
        success = adapter.add_idea(node_data)
        assert success, "Failed to add node"
        print("    [OK] Node created successfully")
        
        # Test 2: Get ideas
        print("  - Testing node retrieval...")
        ideas = adapter.get_ideas()
        assert len(ideas) == 1, f"Expected 1 node, got {len(ideas)}"
        assert ideas[0]['label'] == 'Test Node', "Node label mismatch"
        print("    [OK] Node retrieved successfully")
        
        # Test 3: Set central node
        print("  - Testing central node management...")
        node_id = ideas[0]['id']
        success = adapter.set_central(node_id)
        assert success, "Failed to set central node"
        
        central_id = adapter.get_central()
        assert central_id == node_id, "Central node ID mismatch"
        print("    [OK] Central node set successfully")
        
        # Test 4: Update position
        print("  - Testing position update...")
        success = adapter.update_node_position(node_id, 300, 400)
        assert success, "Failed to update position"
        
        updated_ideas = adapter.get_ideas()
        updated_node = updated_ideas[0]
        assert updated_node['x'] == 300, f"Expected x=300, got {updated_node['x']}"
        assert updated_node['y'] == 400, f"Expected y=400, got {updated_node['y']}"
        print("    [OK] Position updated successfully")
        
        # Test 5: Search functionality
        print("  - Testing search functionality...")
        results = adapter.search_nodes('Test')
        assert len(results) == 1, f"Expected 1 search result, got {len(results)}"
        print("    [OK] Search working correctly")
        
        # Test 6: Statistics
        print("  - Testing statistics...")
        stats = adapter.get_statistics()
        assert stats['total_nodes'] == 1, f"Expected 1 node in stats, got {stats['total_nodes']}"
        assert stats['urgency_distribution']['high'] == 1, "Urgency distribution incorrect"
        print("    [OK] Statistics working correctly")
        
        # Test 7: Backup and restore
        print("  - Testing backup functionality...")
        backup_path = adapter.create_backup()
        assert backup_path is not None, "Failed to create backup"
        assert Path(backup_path).exists(), "Backup file doesn't exist"
        print("    [OK] Backup created successfully")
        
        print("All tests passed! Service adapter is working correctly.")
        return True


def test_configuration_system():
    """Test the configuration system."""
    print("Testing Configuration System...")
    
    # Test default configuration
    from src.infrastructure.config import ConfigFactory
    config = ConfigFactory.create_config("development")
    
    assert config.environment.value == "development"
    assert config.data_file == "mindmap_data.json"
    assert config.cache_size == 100  # DevelopmentConfig has cache_size = 100
    print("  [OK] Default configuration loaded correctly")
    
    # Test environment variable override
    os.environ['MINDMAP_CACHE_SIZE'] = '2000'
    config = ConfigFactory.create_config("development")
    assert config.cache_size == 2000
    print("  [OK] Environment variable override working")
    
    # Clean up
    del os.environ['MINDMAP_CACHE_SIZE']
    
    print("Configuration system tests passed!")
    return True


def test_domain_models():
    """Test domain models directly."""
    print("Testing Domain Models...")
    
    from src.domain.models import Node, Position, UrgencyLevel, EdgeType
    
    # Test Position
    pos = Position(10.5, 20.3)
    assert pos.x == 10.5
    assert pos.y == 20.3
    print("  [OK] Position model working")
    
    # Test Node
    node = Node(
        id=1,
        label="Test Node",
        position=pos,
        urgency=UrgencyLevel.HIGH,
        edge_type=EdgeType.STRONG
    )
    
    assert node.id == 1
    assert node.label == "Test Node"
    assert node.urgency == UrgencyLevel.HIGH
    assert node.is_valid()
    print("  [OK] Node model working")
    
    # Test validation
    invalid_node = Node(id=2, label="")  # Empty label
    errors = invalid_node.validate()
    assert len(errors) > 0
    print("  [OK] Node validation working")
    
    print("Domain model tests passed!")
    return True


def main():
    """Run all tests."""
    print("Testing Enhanced Mind Map - New Architecture Integration")
    print("=" * 60)
    
    try:
        # Test domain models
        test_domain_models()
        print()
        
        # Test configuration system
        test_configuration_system()
        print()
        
        # Test service adapter
        test_service_adapter_basic_functionality()
        print()
        
        print("ALL TESTS PASSED!")
        print("New architecture is working correctly")
        print("Service adapter provides backward compatibility")
        print("Ready for UI integration")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)