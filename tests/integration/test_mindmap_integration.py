"""
Integration tests for the mind map application.

These tests verify that all components work together correctly.
"""

import pytest
import tempfile
from pathlib import Path

from src.domain.models import Node, MindMapData, Position, UrgencyLevel, EdgeType
from src.infrastructure.repositories import JsonMindMapRepository
from src.infrastructure.config import AppConfig
from src.application.services import MindMapService, NodeCreateRequest, NodeUpdateRequest


class TestMindMapIntegration:
    """Integration tests for the complete mind map system."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a real config with temporary paths
            config = AppConfig(
                data_file=str(temp_path / "test_mindmap.json"),
                backup_dir=str(temp_path / "backups"),
                log_dir=str(temp_path / "logs"),
                environment="testing"
            )
            
            yield config
    
    @pytest.fixture
    def service(self, temp_config):
        """Create a complete service stack for testing."""
        repository = JsonMindMapRepository(temp_config)
        service = MindMapService(repository, temp_config)
        return service
    
    def test_complete_mindmap_workflow(self, service):
        """Test a complete mind map workflow from creation to persistence."""
        
        # 1. Create root node
        root_request = NodeCreateRequest(
            label="Project Planning",
            description="Main project planning node",
            urgency=UrgencyLevel.HIGH,
            tag="work"
        )
        
        root_result = service.create_node(root_request)
        assert root_result.is_ok()
        root_node = root_result.data
        
        # 2. Set as central node
        central_result = service.set_central_node(root_node.id)
        assert central_result.is_ok()
        
        # 3. Create child nodes
        child1_request = NodeCreateRequest(
            label="Requirements Analysis",
            description="Analyze project requirements",
            parent_id=root_node.id,
            urgency=UrgencyLevel.HIGH,
            tag="work",
            edge_type=EdgeType.STRONG
        )
        
        child1_result = service.create_node(child1_request)
        assert child1_result.is_ok()
        child1_node = child1_result.data
        
        child2_request = NodeCreateRequest(
            label="Design Phase",
            description="Create system design",
            parent_id=root_node.id,
            urgency=UrgencyLevel.MEDIUM,
            tag="work",
            edge_type=EdgeType.DEFAULT
        )
        
        child2_result = service.create_node(child2_request)
        assert child2_result.is_ok()
        child2_node = child2_result.data
        
        # 4. Create grandchild
        grandchild_request = NodeCreateRequest(
            label="Database Design",
            description="Design database schema",
            parent_id=child2_node.id,
            urgency=UrgencyLevel.MEDIUM,
            tag="technical",
            edge_type=EdgeType.DEPENDENCY
        )
        
        grandchild_result = service.create_node(grandchild_request)
        assert grandchild_result.is_ok()
        grandchild_node = grandchild_result.data
        
        # 5. Verify structure
        all_nodes = service.get_all_nodes()
        assert len(all_nodes) == 4
        
        # Check relationships
        root_children = service.get_children(root_node.id)
        assert len(root_children) == 2
        assert child1_node in root_children
        assert child2_node in root_children
        
        child2_children = service.get_children(child2_node.id)
        assert len(child2_children) == 1
        assert grandchild_node in child2_children
        
        # Check central node
        central_node = service.get_central_node()
        assert central_node == root_node
        
        # 6. Update node positions
        update_request = NodeUpdateRequest(position=Position(100, 200))
        update_result = service.update_node(root_node.id, update_request)
        assert update_result.is_ok()
        
        # 7. Search functionality
        search_results = service.search_nodes("Design")
        assert len(search_results) == 2  # "Design Phase" and "Database Design"
        
        # 8. Filter by tag
        work_nodes = service.get_nodes_by_tag("work")
        assert len(work_nodes) == 3
        
        technical_nodes = service.get_nodes_by_tag("technical")
        assert len(technical_nodes) == 1
        
        # 9. Filter by urgency
        high_urgency_nodes = service.get_nodes_by_urgency(UrgencyLevel.HIGH)
        assert len(high_urgency_nodes) == 2
        
        # 10. Get statistics
        stats = service.get_statistics()
        assert stats["total_nodes"] == 4
        assert stats["root_nodes"] == 1
        assert stats["max_depth"] == 3
        assert stats["urgency_distribution"]["high"] == 2
        assert stats["urgency_distribution"]["medium"] == 2
        assert stats["tag_distribution"]["work"] == 3
        assert stats["tag_distribution"]["technical"] == 1
    
    def test_persistence_across_service_instances(self, temp_config):
        """Test that data persists across different service instances."""
        
        # Create first service instance and add data
        repository1 = JsonMindMapRepository(temp_config)
        service1 = MindMapService(repository1, temp_config)
        
        node_request = NodeCreateRequest(
            label="Persistent Node",
            description="This should persist",
            position=Position(50, 75),
            urgency=UrgencyLevel.HIGH,
            tag="persistent"
        )
        
        result = service1.create_node(node_request)
        assert result.is_ok()
        created_node = result.data
        
        service1.set_central_node(created_node.id)
        
        # Create second service instance (simulating app restart)
        repository2 = JsonMindMapRepository(temp_config)
        service2 = MindMapService(repository2, temp_config)
        
        # Verify data was loaded
        all_nodes = service2.get_all_nodes()
        assert len(all_nodes) == 1
        
        loaded_node = all_nodes[0]
        assert loaded_node.label == "Persistent Node"
        assert loaded_node.description == "This should persist"
        assert loaded_node.position.x == 50
        assert loaded_node.position.y == 75
        assert loaded_node.urgency == UrgencyLevel.HIGH
        assert loaded_node.tag == "persistent"
        
        # Verify central node
        central_node = service2.get_central_node()
        assert central_node is not None
        assert central_node.id == created_node.id
        
        # Verify next ID is correct
        new_node_result = service2.create_node(NodeCreateRequest(label="New Node"))
        assert new_node_result.is_ok()
        assert new_node_result.data.id == created_node.id + 1
    
    def test_backup_and_restore_workflow(self, service):
        """Test complete backup and restore workflow."""
        
        # Create initial data
        root_result = service.create_node(NodeCreateRequest(
            label="Original Root",
            description="Original description"
        ))
        root_id = root_result.data.id
        
        child_result = service.create_node(NodeCreateRequest(
            label="Original Child",
            parent_id=root_id
        ))
        
        service.set_central_node(root_id)
        
        # Create backup
        backup_result = service.create_backup()
        assert backup_result.is_ok()
        backup_path = backup_result.data
        
        # Modify data
        service.update_node(root_id, NodeUpdateRequest(
            label="Modified Root",
            description="Modified description"
        ))
        
        service.create_node(NodeCreateRequest(label="New Node"))
        
        # Verify modifications
        modified_root = service.get_node(root_id).data
        assert modified_root.label == "Modified Root"
        assert len(service.get_all_nodes()) == 3
        
        # Restore from backup
        restore_result = service.restore_backup(backup_path)
        assert restore_result.is_ok()
        
        # Verify restoration
        restored_root = service.get_node(root_id).data
        assert restored_root.label == "Original Root"
        assert restored_root.description == "Original description"
        assert len(service.get_all_nodes()) == 2
        
        # Verify central node is still set
        central_node = service.get_central_node()
        assert central_node is not None
        assert central_node.id == root_id
    
    def test_complex_node_relationships(self, service):
        """Test complex node relationship scenarios."""
        
        # Create a complex hierarchy
        #     Root
        #    /    \
        #   A      B
        #  / \      \
        # C   D      E
        #     |
        #     F
        
        root = service.create_node(NodeCreateRequest(label="Root")).data
        
        node_a = service.create_node(NodeCreateRequest(
            label="A", 
            parent_id=root.id
        )).data
        
        node_b = service.create_node(NodeCreateRequest(
            label="B", 
            parent_id=root.id
        )).data
        
        node_c = service.create_node(NodeCreateRequest(
            label="C", 
            parent_id=node_a.id
        )).data
        
        node_d = service.create_node(NodeCreateRequest(
            label="D", 
            parent_id=node_a.id
        )).data
        
        node_e = service.create_node(NodeCreateRequest(
            label="E", 
            parent_id=node_b.id
        )).data
        
        node_f = service.create_node(NodeCreateRequest(
            label="F", 
            parent_id=node_d.id
        )).data
        
        # Test hierarchy queries
        assert len(service.get_root_nodes()) == 1
        assert len(service.get_children(root.id)) == 2
        assert len(service.get_children(node_a.id)) == 2
        assert len(service.get_children(node_b.id)) == 1
        assert len(service.get_children(node_d.id)) == 1
        
        # Test statistics
        stats = service.get_statistics()
        assert stats["total_nodes"] == 7
        assert stats["root_nodes"] == 1
        assert stats["max_depth"] == 4  # Root -> A -> D -> F
        
        # Test deletion with cascading
        delete_result = service.delete_node(node_a.id)
        assert delete_result.is_ok()
        assert delete_result.data["deleted_count"] == 4  # A, C, D, F
        
        # Verify remaining structure
        remaining_nodes = service.get_all_nodes()
        assert len(remaining_nodes) == 3  # Root, B, E
        
        remaining_labels = [node.label for node in remaining_nodes]
        assert "Root" in remaining_labels
        assert "B" in remaining_labels
        assert "E" in remaining_labels
    
    def test_error_handling_and_recovery(self, service):
        """Test error handling and recovery scenarios."""
        
        # Create valid node
        valid_result = service.create_node(NodeCreateRequest(label="Valid Node"))
        assert valid_result.is_ok()
        valid_id = valid_result.data.id
        
        # Try to create node with invalid parent
        invalid_result = service.create_node(NodeCreateRequest(
            label="Invalid Node",
            parent_id=999
        ))
        assert not invalid_result.is_ok()
        
        # Verify valid node still exists
        assert len(service.get_all_nodes()) == 1
        
        # Try to update non-existent node
        update_result = service.update_node(999, NodeUpdateRequest(label="Updated"))
        assert not update_result.is_ok()
        
        # Try to delete non-existent node
        delete_result = service.delete_node(999)
        assert not delete_result.is_ok()
        
        # Verify valid node still exists and is unchanged
        remaining_nodes = service.get_all_nodes()
        assert len(remaining_nodes) == 1
        assert remaining_nodes[0].label == "Valid Node"
        
        # Try to create circular reference
        child_result = service.create_node(NodeCreateRequest(
            label="Child",
            parent_id=valid_id
        ))
        assert child_result.is_ok()
        child_id = child_result.data.id
        
        # Try to make parent a child of child
        circular_result = service.update_node(valid_id, NodeUpdateRequest(
            parent_id=child_id
        ))
        assert not circular_result.is_ok()
        assert "circular reference" in circular_result.error.lower()
        
        # Verify structure is unchanged
        parent_node = service.get_node(valid_id).data
        child_node = service.get_node(child_id).data
        assert parent_node.parent_id is None
        assert child_node.parent_id == valid_id