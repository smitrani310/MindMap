"""
Unit tests for application services.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.domain.models import Node, MindMapData, Position, UrgencyLevel, EdgeType
from src.application.services import (
    MindMapService, NodeCreateRequest, NodeUpdateRequest, ServiceError
)
from src.infrastructure.repositories import Result, InMemoryMindMapRepository
from src.infrastructure.config import AppConfig


class TestNodeCreateRequest:
    """Test cases for NodeCreateRequest."""
    
    def test_create_request_minimal(self):
        """Test creating request with minimal fields."""
        request = NodeCreateRequest(label="Test Node")
        
        assert request.label == "Test Node"
        assert request.description == ""
        assert request.position == Position.origin()
        assert request.urgency == UrgencyLevel.MEDIUM
        assert request.tag == ""
        assert request.parent_id is None
        assert request.edge_type == EdgeType.DEFAULT
    
    def test_create_request_full(self):
        """Test creating request with all fields."""
        pos = Position(10, 20)
        request = NodeCreateRequest(
            label="Test Node",
            description="Test Description",
            position=pos,
            urgency=UrgencyLevel.HIGH,
            tag="test",
            parent_id=1,
            edge_type=EdgeType.STRONG
        )
        
        assert request.label == "Test Node"
        assert request.description == "Test Description"
        assert request.position == pos
        assert request.urgency == UrgencyLevel.HIGH
        assert request.tag == "test"
        assert request.parent_id == 1
        assert request.edge_type == EdgeType.STRONG


class TestNodeUpdateRequest:
    """Test cases for NodeUpdateRequest."""
    
    def test_update_request_empty(self):
        """Test creating empty update request."""
        request = NodeUpdateRequest()
        
        assert request.label is None
        assert request.description is None
        assert request.position is None
        assert request.urgency is None
        assert request.tag is None
        assert request.parent_id is None
        assert request.edge_type is None
    
    def test_update_request_partial(self):
        """Test creating partial update request."""
        request = NodeUpdateRequest(
            label="New Label",
            urgency=UrgencyLevel.HIGH
        )
        
        assert request.label == "New Label"
        assert request.urgency == UrgencyLevel.HIGH
        assert request.description is None
        assert request.position is None


class TestMindMapService:
    """Test cases for MindMapService."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=AppConfig)
        config.cache_size = 100
        return config
    
    @pytest.fixture
    def service(self, mock_config):
        """Create a MindMapService with in-memory repository."""
        repository = InMemoryMindMapRepository()
        service = MindMapService(repository, mock_config)
        return service
    
    def test_service_initialization(self, mock_config):
        """Test service initialization."""
        repository = InMemoryMindMapRepository()
        service = MindMapService(repository, mock_config)
        
        assert service.repository == repository
        assert service.config == mock_config
        assert service._next_id == 1
        assert len(service.get_all_nodes()) == 0
    
    def test_service_initialization_with_existing_data(self, mock_config):
        """Test service initialization with existing data."""
        # Pre-populate repository
        repository = InMemoryMindMapRepository()
        existing_node = Node(id=5, label="Existing")
        mindmap = MindMapData(nodes=[existing_node])
        repository.save(mindmap)
        
        # Create service
        service = MindMapService(repository, mock_config)
        
        # Next ID should be set based on existing data
        assert service._next_id == 6
        assert len(service.get_all_nodes()) == 1
    
    def test_create_node_success(self, service):
        """Test successful node creation."""
        request = NodeCreateRequest(
            label="Test Node",
            description="Test Description",
            urgency=UrgencyLevel.HIGH
        )
        
        result = service.create_node(request)
        
        assert result.is_ok()
        created_node = result.data
        assert created_node.id == 1
        assert created_node.label == "Test Node"
        assert created_node.description == "Test Description"
        assert created_node.urgency == UrgencyLevel.HIGH
        
        # Verify node was added to service
        all_nodes = service.get_all_nodes()
        assert len(all_nodes) == 1
        assert all_nodes[0] == created_node
    
    def test_create_node_with_parent(self, service):
        """Test creating node with parent."""
        # Create parent first
        parent_request = NodeCreateRequest(label="Parent")
        parent_result = service.create_node(parent_request)
        parent_id = parent_result.data.id
        
        # Create child
        child_request = NodeCreateRequest(
            label="Child",
            parent_id=parent_id,
            edge_type=EdgeType.STRONG
        )
        
        result = service.create_node(child_request)
        
        assert result.is_ok()
        child_node = result.data
        assert child_node.parent_id == parent_id
        assert child_node.edge_type == EdgeType.STRONG
    
    def test_create_node_invalid_parent(self, service):
        """Test creating node with non-existent parent."""
        request = NodeCreateRequest(
            label="Test Node",
            parent_id=999  # Non-existent parent
        )
        
        result = service.create_node(request)
        
        assert not result.is_ok()
        assert "Parent node with id 999 not found" in result.error
    
    def test_create_node_validation_error(self, service):
        """Test creating node with validation error."""
        request = NodeCreateRequest(label="")  # Empty label
        
        result = service.create_node(request)
        
        assert not result.is_ok()
        assert "validation failed" in result.error.lower()
    
    def test_update_node_success(self, service):
        """Test successful node update."""
        # Create node first
        create_request = NodeCreateRequest(label="Original")
        create_result = service.create_node(create_request)
        node_id = create_result.data.id
        
        # Update node
        update_request = NodeUpdateRequest(
            label="Updated",
            description="New Description",
            urgency=UrgencyLevel.HIGH
        )
        
        result = service.update_node(node_id, update_request)
        
        assert result.is_ok()
        updated_node = result.data
        assert updated_node.label == "Updated"
        assert updated_node.description == "New Description"
        assert updated_node.urgency == UrgencyLevel.HIGH
        assert updated_node.id == node_id  # ID should remain the same
    
    def test_update_node_position(self, service):
        """Test updating node position."""
        # Create node
        create_request = NodeCreateRequest(label="Test")
        create_result = service.create_node(create_request)
        node_id = create_result.data.id
        
        # Update position
        new_position = Position(100, 200)
        update_request = NodeUpdateRequest(position=new_position)
        
        result = service.update_node(node_id, update_request)
        
        assert result.is_ok()
        updated_node = result.data
        assert updated_node.position == new_position
    
    def test_update_node_parent(self, service):
        """Test updating node parent."""
        # Create nodes
        parent_result = service.create_node(NodeCreateRequest(label="Parent"))
        child_result = service.create_node(NodeCreateRequest(label="Child"))
        
        parent_id = parent_result.data.id
        child_id = child_result.data.id
        
        # Update child's parent
        update_request = NodeUpdateRequest(
            parent_id=parent_id,
            edge_type=EdgeType.STRONG
        )
        
        result = service.update_node(child_id, update_request)
        
        assert result.is_ok()
        updated_node = result.data
        assert updated_node.parent_id == parent_id
        assert updated_node.edge_type == EdgeType.STRONG
    
    def test_update_node_nonexistent(self, service):
        """Test updating non-existent node."""
        update_request = NodeUpdateRequest(label="Updated")
        
        result = service.update_node(999, update_request)
        
        assert not result.is_ok()
        assert "Node with id 999 not found" in result.error
    
    def test_update_node_invalid_parent(self, service):
        """Test updating node with invalid parent."""
        # Create node
        create_result = service.create_node(NodeCreateRequest(label="Test"))
        node_id = create_result.data.id
        
        # Try to set non-existent parent
        update_request = NodeUpdateRequest(parent_id=999)
        
        result = service.update_node(node_id, update_request)
        
        assert not result.is_ok()
        assert "Parent node with id 999 not found" in result.error
    
    def test_update_node_circular_reference(self, service):
        """Test updating node to create circular reference."""
        # Create parent and child
        parent_result = service.create_node(NodeCreateRequest(label="Parent"))
        child_result = service.create_node(NodeCreateRequest(
            label="Child", 
            parent_id=parent_result.data.id
        ))
        
        parent_id = parent_result.data.id
        child_id = child_result.data.id
        
        # Try to make parent a child of child (circular reference)
        update_request = NodeUpdateRequest(parent_id=child_id)
        
        result = service.update_node(parent_id, update_request)
        
        assert not result.is_ok()
        assert "Cannot create circular reference" in result.error
    
    def test_delete_node_success(self, service):
        """Test successful node deletion."""
        # Create node
        create_result = service.create_node(NodeCreateRequest(label="Test"))
        node_id = create_result.data.id
        
        result = service.delete_node(node_id)
        
        assert result.is_ok()
        assert result.data["deleted_count"] == 1
        
        # Verify node was deleted
        assert len(service.get_all_nodes()) == 0
    
    def test_delete_node_with_descendants(self, service):
        """Test deleting node with descendants."""
        # Create parent and children
        parent_result = service.create_node(NodeCreateRequest(label="Parent"))
        child1_result = service.create_node(NodeCreateRequest(
            label="Child 1", 
            parent_id=parent_result.data.id
        ))
        child2_result = service.create_node(NodeCreateRequest(
            label="Child 2", 
            parent_id=parent_result.data.id
        ))
        grandchild_result = service.create_node(NodeCreateRequest(
            label="Grandchild", 
            parent_id=child1_result.data.id
        ))
        
        parent_id = parent_result.data.id
        
        # Delete parent (should delete all descendants)
        result = service.delete_node(parent_id)
        
        assert result.is_ok()
        assert result.data["deleted_count"] == 4  # Parent + 2 children + 1 grandchild
        
        # Verify all nodes were deleted
        assert len(service.get_all_nodes()) == 0
    
    def test_delete_node_nonexistent(self, service):
        """Test deleting non-existent node."""
        result = service.delete_node(999)
        
        assert not result.is_ok()
        assert "Node with id 999 not found" in result.error
    
    def test_get_node_success(self, service):
        """Test getting existing node."""
        # Create node
        create_result = service.create_node(NodeCreateRequest(label="Test"))
        node_id = create_result.data.id
        
        result = service.get_node(node_id)
        
        assert result.is_ok()
        retrieved_node = result.data
        assert retrieved_node.id == node_id
        assert retrieved_node.label == "Test"
    
    def test_get_node_nonexistent(self, service):
        """Test getting non-existent node."""
        result = service.get_node(999)
        
        assert not result.is_ok()
        assert "Node with id 999 not found" in result.error
    
    def test_get_children(self, service):
        """Test getting children of a node."""
        # Create parent and children
        parent_result = service.create_node(NodeCreateRequest(label="Parent"))
        child1_result = service.create_node(NodeCreateRequest(
            label="Child 1", 
            parent_id=parent_result.data.id
        ))
        child2_result = service.create_node(NodeCreateRequest(
            label="Child 2", 
            parent_id=parent_result.data.id
        ))
        # Create unrelated node
        service.create_node(NodeCreateRequest(label="Other"))
        
        parent_id = parent_result.data.id
        children = service.get_children(parent_id)
        
        assert len(children) == 2
        child_labels = [child.label for child in children]
        assert "Child 1" in child_labels
        assert "Child 2" in child_labels
    
    def test_get_root_nodes(self, service):
        """Test getting root nodes."""
        # Create root nodes and child
        root1_result = service.create_node(NodeCreateRequest(label="Root 1"))
        root2_result = service.create_node(NodeCreateRequest(label="Root 2"))
        service.create_node(NodeCreateRequest(
            label="Child", 
            parent_id=root1_result.data.id
        ))
        
        root_nodes = service.get_root_nodes()
        
        assert len(root_nodes) == 2
        root_labels = [node.label for node in root_nodes]
        assert "Root 1" in root_labels
        assert "Root 2" in root_labels
    
    def test_set_central_node_success(self, service):
        """Test setting central node."""
        # Create node
        create_result = service.create_node(NodeCreateRequest(label="Central"))
        node_id = create_result.data.id
        
        result = service.set_central_node(node_id)
        
        assert result.is_ok()
        
        # Verify central node was set
        central_node = service.get_central_node()
        assert central_node is not None
        assert central_node.id == node_id
    
    def test_set_central_node_none(self, service):
        """Test clearing central node."""
        # Create and set central node first
        create_result = service.create_node(NodeCreateRequest(label="Central"))
        service.set_central_node(create_result.data.id)
        
        # Clear central node
        result = service.set_central_node(None)
        
        assert result.is_ok()
        
        # Verify central node was cleared
        central_node = service.get_central_node()
        assert central_node is None
    
    def test_set_central_node_nonexistent(self, service):
        """Test setting non-existent central node."""
        result = service.set_central_node(999)
        
        assert not result.is_ok()
        assert "Node with id 999 not found" in result.error
    
    def test_search_nodes(self, service):
        """Test searching nodes."""
        # Create test nodes
        service.create_node(NodeCreateRequest(
            label="JavaScript Tutorial",
            description="Learn JavaScript basics"
        ))
        service.create_node(NodeCreateRequest(
            label="Python Guide",
            description="Advanced Python concepts"
        ))
        service.create_node(NodeCreateRequest(
            label="Web Development",
            description="HTML, CSS, and JavaScript"
        ))
        
        # Search in labels
        results = service.search_nodes("JavaScript")
        assert len(results) == 2  # "JavaScript Tutorial" and "Web Development"
        
        # Search in descriptions
        results = service.search_nodes("Python")
        assert len(results) == 1
        assert results[0].label == "Python Guide"
        
        # Search with no results
        results = service.search_nodes("NonExistent")
        assert len(results) == 0
        
        # Empty search
        results = service.search_nodes("")
        assert len(results) == 0
    
    def test_get_nodes_by_tag(self, service):
        """Test getting nodes by tag."""
        # Create nodes with different tags
        service.create_node(NodeCreateRequest(label="Node 1", tag="work"))
        service.create_node(NodeCreateRequest(label="Node 2", tag="personal"))
        service.create_node(NodeCreateRequest(label="Node 3", tag="work"))
        service.create_node(NodeCreateRequest(label="Node 4", tag=""))
        
        # Get work nodes
        work_nodes = service.get_nodes_by_tag("work")
        assert len(work_nodes) == 2
        
        # Get personal nodes
        personal_nodes = service.get_nodes_by_tag("personal")
        assert len(personal_nodes) == 1
        
        # Get non-existent tag
        none_nodes = service.get_nodes_by_tag("nonexistent")
        assert len(none_nodes) == 0
    
    def test_get_nodes_by_urgency(self, service):
        """Test getting nodes by urgency."""
        # Create nodes with different urgencies
        service.create_node(NodeCreateRequest(label="Node 1", urgency=UrgencyLevel.HIGH))
        service.create_node(NodeCreateRequest(label="Node 2", urgency=UrgencyLevel.MEDIUM))
        service.create_node(NodeCreateRequest(label="Node 3", urgency=UrgencyLevel.HIGH))
        service.create_node(NodeCreateRequest(label="Node 4", urgency=UrgencyLevel.LOW))
        
        # Get high urgency nodes
        high_nodes = service.get_nodes_by_urgency(UrgencyLevel.HIGH)
        assert len(high_nodes) == 2
        
        # Get medium urgency nodes
        medium_nodes = service.get_nodes_by_urgency(UrgencyLevel.MEDIUM)
        assert len(medium_nodes) == 1
        
        # Get low urgency nodes
        low_nodes = service.get_nodes_by_urgency(UrgencyLevel.LOW)
        assert len(low_nodes) == 1
    
    def test_get_statistics(self, service):
        """Test getting mind map statistics."""
        # Empty mind map
        stats = service.get_statistics()
        assert stats["total_nodes"] == 0
        assert stats["root_nodes"] == 0
        assert stats["max_depth"] == 0
        
        # Create test structure
        root1 = service.create_node(NodeCreateRequest(
            label="Root 1", 
            urgency=UrgencyLevel.HIGH,
            tag="work"
        ))
        root2 = service.create_node(NodeCreateRequest(
            label="Root 2",
            urgency=UrgencyLevel.MEDIUM,
            tag="personal"
        ))
        child = service.create_node(NodeCreateRequest(
            label="Child",
            parent_id=root1.data.id,
            urgency=UrgencyLevel.HIGH,
            tag="work"
        ))
        grandchild = service.create_node(NodeCreateRequest(
            label="Grandchild",
            parent_id=child.data.id,
            urgency=UrgencyLevel.LOW,
            tag="personal"
        ))
        
        stats = service.get_statistics()
        assert stats["total_nodes"] == 4
        assert stats["root_nodes"] == 2
        assert stats["max_depth"] == 3  # Root -> Child -> Grandchild
        assert stats["urgency_distribution"]["high"] == 2
        assert stats["urgency_distribution"]["medium"] == 1
        assert stats["urgency_distribution"]["low"] == 1
        assert stats["tag_distribution"]["work"] == 2
        assert stats["tag_distribution"]["personal"] == 2
    
    def test_backup_operations(self, service):
        """Test backup and restore operations."""
        # Create test data
        service.create_node(NodeCreateRequest(label="Test Node"))
        
        # Create backup
        backup_result = service.create_backup()
        assert backup_result.is_ok()
        
        # List backups
        list_result = service.list_backups()
        assert list_result.is_ok()
        assert len(list_result.data) == 1
        
        # Modify data
        service.create_node(NodeCreateRequest(label="Another Node"))
        assert len(service.get_all_nodes()) == 2
        
        # Restore backup
        backup_path = list_result.data[0]["path"]
        restore_result = service.restore_backup(backup_path)
        assert restore_result.is_ok()
        
        # Verify restoration
        assert len(service.get_all_nodes()) == 1
        assert service.get_all_nodes()[0].label == "Test Node"