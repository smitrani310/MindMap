"""
Unit tests for domain models.
"""

import pytest
from datetime import datetime
from src.domain.models import (
    Node, Position, MindMapData, UrgencyLevel, EdgeType, 
    ValidationError, MindMapSettings, MindMapMetadata
)


class TestPosition:
    """Test cases for Position value object."""
    
    def test_position_creation(self):
        """Test creating a position."""
        pos = Position(10.5, -20.3)
        assert pos.x == 10.5
        assert pos.y == -20.3
    
    def test_position_validation_nan(self):
        """Test position validation with NaN values."""
        with pytest.raises(ValidationError, match="Position coordinates cannot be NaN"):
            Position(float('nan'), 0)
    
    def test_position_validation_infinite(self):
        """Test position validation with infinite values."""
        with pytest.raises(ValidationError, match="Position coordinates cannot be infinite"):
            Position(float('inf'), 0)
    
    def test_position_validation_out_of_bounds(self):
        """Test position validation with out-of-bounds values."""
        with pytest.raises(ValidationError, match="Position coordinates are out of reasonable bounds"):
            Position(200000, 0)
    
    def test_distance_calculation(self):
        """Test distance calculation between positions."""
        pos1 = Position(0, 0)
        pos2 = Position(3, 4)
        assert pos1.distance_to(pos2) == 5.0
    
    def test_move_by(self):
        """Test moving position by delta."""
        pos = Position(10, 20)
        new_pos = pos.move_by(5, -3)
        assert new_pos.x == 15
        assert new_pos.y == 17
        # Original position should be unchanged (immutable)
        assert pos.x == 10
        assert pos.y == 20
    
    def test_to_dict(self):
        """Test converting position to dictionary."""
        pos = Position(1.5, -2.7)
        result = pos.to_dict()
        assert result == {"x": 1.5, "y": -2.7}
    
    def test_from_dict(self):
        """Test creating position from dictionary."""
        data = {"x": 1.5, "y": -2.7}
        pos = Position.from_dict(data)
        assert pos.x == 1.5
        assert pos.y == -2.7
    
    def test_origin(self):
        """Test creating position at origin."""
        pos = Position.origin()
        assert pos.x == 0.0
        assert pos.y == 0.0


class TestNode:
    """Test cases for Node entity."""
    
    def test_node_creation_minimal(self):
        """Test creating a node with minimal required fields."""
        node = Node(id=1, label="Test Node")
        assert node.id == 1
        assert node.label == "Test Node"
        assert node.description == ""
        assert node.urgency == UrgencyLevel.MEDIUM
        assert node.parent_id is None
        assert node.edge_type == EdgeType.DEFAULT
    
    def test_node_creation_full(self):
        """Test creating a node with all fields."""
        pos = Position(10, 20)
        node = Node(
            id=1,
            label="Test Node",
            description="Test Description",
            position=pos,
            urgency=UrgencyLevel.HIGH,
            tag="test",
            parent_id=2,
            edge_type=EdgeType.STRONG,
            size=25.0,
            color="#FF0000"
        )
        
        assert node.id == 1
        assert node.label == "Test Node"
        assert node.description == "Test Description"
        assert node.position == pos
        assert node.urgency == UrgencyLevel.HIGH
        assert node.tag == "test"
        assert node.parent_id == 2
        assert node.edge_type == EdgeType.STRONG
        assert node.size == 25.0
        assert node.color == "#FF0000"
    
    def test_node_validation_empty_label(self):
        """Test node validation with empty label."""
        node = Node(id=1, label="")
        errors = node.validate()
        assert len(errors) == 1
        assert "Label cannot be empty" in errors[0].message
    
    def test_node_validation_long_label(self):
        """Test node validation with overly long label."""
        long_label = "x" * 501
        node = Node(id=1, label=long_label)
        errors = node.validate()
        assert len(errors) == 1
        assert "Label cannot exceed 500 characters" in errors[0].message
    
    def test_node_validation_long_description(self):
        """Test node validation with overly long description."""
        long_description = "x" * 5001
        node = Node(id=1, label="Test", description=long_description)
        errors = node.validate()
        assert len(errors) == 1
        assert "Description cannot exceed 5000 characters" in errors[0].message
    
    def test_node_validation_invalid_size(self):
        """Test node validation with invalid size."""
        node = Node(id=1, label="Test", size=0)
        errors = node.validate()
        assert len(errors) == 1
        assert "Size must be between 0 and 200" in errors[0].message
    
    def test_node_validation_invalid_color(self):
        """Test node validation with invalid color."""
        node = Node(id=1, label="Test", color="invalid")
        errors = node.validate()
        assert len(errors) == 1
        assert "Color must be a valid hex color" in errors[0].message
    
    def test_node_validation_self_parent(self):
        """Test node validation with self as parent."""
        node = Node(id=1, label="Test", parent_id=1)
        errors = node.validate()
        assert len(errors) == 1
        assert "Node cannot be its own parent" in errors[0].message
    
    def test_node_is_valid(self):
        """Test node validity check."""
        valid_node = Node(id=1, label="Test")
        assert valid_node.is_valid()
        
        invalid_node = Node(id=1, label="")
        assert not invalid_node.is_valid()
    
    def test_node_update_position(self):
        """Test updating node position."""
        node = Node(id=1, label="Test")
        new_pos = Position(10, 20)
        updated_node = node.update_position(new_pos)
        
        assert updated_node.position == new_pos
        assert updated_node.id == node.id
        assert updated_node.label == node.label
        # Original node should be unchanged
        assert node.position != new_pos
    
    def test_node_update_label(self):
        """Test updating node label."""
        node = Node(id=1, label="Old Label")
        updated_node = node.update_label("New Label")
        
        assert updated_node.label == "New Label"
        assert updated_node.id == node.id
        # Original node should be unchanged
        assert node.label == "Old Label"
    
    def test_node_set_parent(self):
        """Test setting node parent."""
        node = Node(id=1, label="Test")
        updated_node = node.set_parent(2, EdgeType.STRONG)
        
        assert updated_node.parent_id == 2
        assert updated_node.edge_type == EdgeType.STRONG
        # Original node should be unchanged
        assert node.parent_id is None
    
    def test_node_calculate_size(self):
        """Test node size calculation."""
        node = Node(id=1, label="Short")
        size = node.calculate_size()
        assert size > 0
        
        long_node = Node(id=2, label="This is a much longer label for testing")
        long_size = long_node.calculate_size()
        assert long_size > size
        
        high_urgency_node = Node(id=3, label="Short", urgency=UrgencyLevel.HIGH)
        high_size = high_urgency_node.calculate_size()
        assert high_size > size
    
    def test_node_to_dict(self):
        """Test converting node to dictionary."""
        pos = Position(10, 20)
        node = Node(
            id=1,
            label="Test",
            description="Description",
            position=pos,
            urgency=UrgencyLevel.HIGH,
            tag="test"
        )
        
        result = node.to_dict()
        assert result["id"] == 1
        assert result["label"] == "Test"
        assert result["description"] == "Description"
        assert result["position"] == {"x": 10, "y": 20}
        assert result["urgency"] == "high"
        assert result["tag"] == "test"
    
    def test_node_from_dict(self):
        """Test creating node from dictionary."""
        data = {
            "id": 1,
            "label": "Test",
            "description": "Description",
            "position": {"x": 10, "y": 20},
            "urgency": "high",
            "tag": "test",
            "parent_id": 2,
            "edge_type": "strong",
            "size": 25.0,
            "color": "#FF0000",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        node = Node.from_dict(data)
        assert node.id == 1
        assert node.label == "Test"
        assert node.description == "Description"
        assert node.position.x == 10
        assert node.position.y == 20
        assert node.urgency == UrgencyLevel.HIGH
        assert node.tag == "test"
        assert node.parent_id == 2
        assert node.edge_type == EdgeType.STRONG
        assert node.size == 25.0
        assert node.color == "#FF0000"


class TestMindMapData:
    """Test cases for MindMapData aggregate root."""
    
    def test_mindmap_creation_empty(self):
        """Test creating empty mind map."""
        mindmap = MindMapData()
        assert len(mindmap.nodes) == 0
        assert mindmap.central_node_id is None
        assert mindmap.metadata.node_count == 0
    
    def test_mindmap_add_node(self):
        """Test adding a node to mind map."""
        mindmap = MindMapData()
        node = Node(id=1, label="Test")
        
        updated_mindmap = mindmap.add_node(node)
        assert len(updated_mindmap.nodes) == 1
        assert updated_mindmap.nodes[0] == node
        assert updated_mindmap.metadata.node_count == 1
        
        # Original mindmap should be unchanged
        assert len(mindmap.nodes) == 0
    
    def test_mindmap_add_duplicate_node(self):
        """Test adding a node with duplicate ID."""
        node1 = Node(id=1, label="Test 1")
        node2 = Node(id=1, label="Test 2")
        
        mindmap = MindMapData(nodes=[node1])
        
        with pytest.raises(ValidationError, match="Node with id 1 already exists"):
            mindmap.add_node(node2)
    
    def test_mindmap_update_node(self):
        """Test updating a node in mind map."""
        node = Node(id=1, label="Original")
        mindmap = MindMapData(nodes=[node])
        
        updated_node = node.update_label("Updated")
        updated_mindmap = mindmap.update_node(updated_node)
        
        assert updated_mindmap.nodes[0].label == "Updated"
        # Original mindmap should be unchanged
        assert mindmap.nodes[0].label == "Original"
    
    def test_mindmap_update_nonexistent_node(self):
        """Test updating a non-existent node."""
        mindmap = MindMapData()
        node = Node(id=1, label="Test")
        
        with pytest.raises(ValidationError, match="Node with id 1 not found"):
            mindmap.update_node(node)
    
    def test_mindmap_remove_node(self):
        """Test removing a node from mind map."""
        parent = Node(id=1, label="Parent")
        child = Node(id=2, label="Child", parent_id=1)
        grandchild = Node(id=3, label="Grandchild", parent_id=2)
        
        mindmap = MindMapData(nodes=[parent, child, grandchild])
        
        # Remove parent should remove all descendants
        updated_mindmap = mindmap.remove_node(1)
        assert len(updated_mindmap.nodes) == 0
    
    def test_mindmap_find_node_by_id(self):
        """Test finding a node by ID."""
        node = Node(id=1, label="Test")
        mindmap = MindMapData(nodes=[node])
        
        found_node = mindmap.find_node_by_id(1)
        assert found_node == node
        
        not_found = mindmap.find_node_by_id(999)
        assert not_found is None
    
    def test_mindmap_get_children(self):
        """Test getting children of a node."""
        parent = Node(id=1, label="Parent")
        child1 = Node(id=2, label="Child 1", parent_id=1)
        child2 = Node(id=3, label="Child 2", parent_id=1)
        other = Node(id=4, label="Other")
        
        mindmap = MindMapData(nodes=[parent, child1, child2, other])
        children = mindmap.get_children(1)
        
        assert len(children) == 2
        assert child1 in children
        assert child2 in children
        assert other not in children
    
    def test_mindmap_get_descendants(self):
        """Test getting all descendants of a node."""
        parent = Node(id=1, label="Parent")
        child = Node(id=2, label="Child", parent_id=1)
        grandchild = Node(id=3, label="Grandchild", parent_id=2)
        
        mindmap = MindMapData(nodes=[parent, child, grandchild])
        descendants = mindmap.get_descendants(1)
        
        assert descendants == {2, 3}
    
    def test_mindmap_get_root_nodes(self):
        """Test getting root nodes."""
        root1 = Node(id=1, label="Root 1")
        root2 = Node(id=2, label="Root 2")
        child = Node(id=3, label="Child", parent_id=1)
        
        mindmap = MindMapData(nodes=[root1, root2, child])
        roots = mindmap.get_root_nodes()
        
        assert len(roots) == 2
        assert root1 in roots
        assert root2 in roots
        assert child not in roots
    
    def test_mindmap_validate_relationships(self):
        """Test validating node relationships."""
        # Valid relationships
        parent = Node(id=1, label="Parent")
        child = Node(id=2, label="Child", parent_id=1)
        mindmap = MindMapData(nodes=[parent, child])
        
        errors = mindmap.validate_relationships()
        assert len(errors) == 0
        
        # Invalid relationship - non-existent parent
        orphan = Node(id=3, label="Orphan", parent_id=999)
        invalid_mindmap = MindMapData(nodes=[parent, child, orphan])
        
        errors = invalid_mindmap.validate_relationships()
        assert len(errors) == 1
        assert "non-existent parent" in errors[0].message
    
    def test_mindmap_would_create_cycle(self):
        """Test cycle detection."""
        node1 = Node(id=1, label="Node 1", parent_id=2)
        node2 = Node(id=2, label="Node 2")
        mindmap = MindMapData(nodes=[node1, node2])
        
        # This would create a cycle: 2 -> 1 -> 2
        assert mindmap._would_create_cycle(2, 1) == True
        
        # This would not create a cycle
        assert mindmap._would_create_cycle(1, 3) == False
    
    def test_mindmap_to_dict(self):
        """Test converting mind map to dictionary."""
        node = Node(id=1, label="Test")
        mindmap = MindMapData(nodes=[node], central_node_id=1)
        
        result = mindmap.to_dict()
        assert "nodes" in result
        assert "central_node_id" in result
        assert "settings" in result
        assert "metadata" in result
        assert len(result["nodes"]) == 1
        assert result["central_node_id"] == 1
    
    def test_mindmap_from_dict(self):
        """Test creating mind map from dictionary."""
        data = {
            "nodes": [
                {
                    "id": 1,
                    "label": "Test",
                    "description": "",
                    "position": {"x": 0, "y": 0},
                    "urgency": "medium",
                    "tag": "",
                    "parent_id": None,
                    "edge_type": "default",
                    "size": 20.0,
                    "color": "#EEEEEE",
                    "created_at": "2023-01-01T00:00:00",
                    "updated_at": "2023-01-01T00:00:00"
                }
            ],
            "central_node_id": 1,
            "settings": {},
            "metadata": {}
        }
        
        mindmap = MindMapData.from_dict(data)
        assert len(mindmap.nodes) == 1
        assert mindmap.nodes[0].label == "Test"
        assert mindmap.central_node_id == 1