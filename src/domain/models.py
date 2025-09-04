"""
Domain models for the Enhanced Mind Map application.

This module contains the core domain entities and value objects that represent
the business concepts of the mind mapping application.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Set
from uuid import uuid4


class UrgencyLevel(str, Enum):
    """Urgency levels for nodes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EdgeType(str, Enum):
    """Types of edges between nodes."""
    DEFAULT = "default"
    STRONG = "strong"
    WEAK = "weak"
    DEPENDENCY = "dependency"
    RELATION = "relation"
    INFLUENCE = "influence"


class ValidationError(Exception):
    """Raised when domain model validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


@dataclass(frozen=True)
class Position:
    """Value object representing a 2D position."""
    x: float
    y: float
    
    def __post_init__(self):
        """Validate position values."""
        if math.isnan(self.x) or math.isnan(self.y):
            raise ValidationError("Position coordinates cannot be NaN")
        if math.isinf(self.x) or math.isinf(self.y):
            raise ValidationError("Position coordinates cannot be infinite")
        if abs(self.x) > 100000 or abs(self.y) > 100000:
            raise ValidationError("Position coordinates are out of reasonable bounds")
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance to another position."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def move_by(self, dx: float, dy: float) -> 'Position':
        """Create a new position moved by the given deltas."""
        return Position(self.x + dx, self.y + dy)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary representation."""
        return {"x": self.x, "y": self.y}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create Position from dictionary."""
        return cls(x=float(data["x"]), y=float(data["y"]))
    
    @classmethod
    def origin(cls) -> 'Position':
        """Create position at origin (0, 0)."""
        return cls(0.0, 0.0)


@dataclass
class Node:
    """Core domain entity representing a mind map node."""
    
    # Identity
    id: int
    
    # Core attributes
    label: str
    description: str = ""
    position: Position = field(default_factory=Position.origin)
    
    # Classification
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    tag: str = ""
    
    # Relationships
    parent_id: Optional[int] = None
    edge_type: EdgeType = EdgeType.DEFAULT
    
    # Visual properties
    size: float = 20.0
    color: str = "#EEEEEE"
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate node after initialization."""
        self.validate()
    
    def validate(self) -> List[ValidationError]:
        """
        Validate the node and return list of validation errors.
        
        Returns:
            List of ValidationError instances. Empty list if valid.
        """
        errors = []
        
        # Validate label
        if not self.label or not self.label.strip():
            errors.append(ValidationError("Label cannot be empty", "label"))
        elif len(self.label) > 500:
            errors.append(ValidationError("Label cannot exceed 500 characters", "label"))
        
        # Validate description
        if len(self.description) > 5000:
            errors.append(ValidationError("Description cannot exceed 5000 characters", "description"))
        
        # Validate size
        if self.size <= 0 or self.size > 200:
            errors.append(ValidationError("Size must be between 0 and 200", "size"))
        
        # Validate color (basic hex color validation)
        if self.color and not (self.color.startswith('#') and len(self.color) == 7):
            try:
                # Try to validate as hex color
                int(self.color[1:], 16)
            except (ValueError, IndexError):
                errors.append(ValidationError("Color must be a valid hex color", "color"))
        
        # Validate parent relationship (cannot be parent of itself)
        if self.parent_id == self.id:
            errors.append(ValidationError("Node cannot be its own parent", "parent_id"))
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the node is valid."""
        return len(self.validate()) == 0
    
    def update_position(self, new_position: Position) -> 'Node':
        """Create a new node with updated position."""
        return self._update(position=new_position)
    
    def update_label(self, new_label: str) -> 'Node':
        """Create a new node with updated label."""
        return self._update(label=new_label.strip())
    
    def update_description(self, new_description: str) -> 'Node':
        """Create a new node with updated description."""
        return self._update(description=new_description)
    
    def update_urgency(self, new_urgency: UrgencyLevel) -> 'Node':
        """Create a new node with updated urgency."""
        return self._update(urgency=new_urgency)
    
    def update_tag(self, new_tag: str) -> 'Node':
        """Create a new node with updated tag."""
        return self._update(tag=new_tag.strip())
    
    def set_parent(self, parent_id: Optional[int], edge_type: EdgeType = EdgeType.DEFAULT) -> 'Node':
        """Create a new node with updated parent relationship."""
        return self._update(parent_id=parent_id, edge_type=edge_type)
    
    def _update(self, **kwargs) -> 'Node':
        """Create a new node with updated fields."""
        # Update the updated_at timestamp
        kwargs['updated_at'] = datetime.now()
        
        # Create new node with updated fields
        updated_data = {
            'id': self.id,
            'label': self.label,
            'description': self.description,
            'position': self.position,
            'urgency': self.urgency,
            'tag': self.tag,
            'parent_id': self.parent_id,
            'edge_type': self.edge_type,
            'size': self.size,
            'color': self.color,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
        updated_data.update(kwargs)
        
        return Node(**updated_data)
    
    def calculate_size(self, base_size: float = 20.0, urgency_multiplier: Dict[UrgencyLevel, float] = None) -> float:
        """
        Calculate node size based on label length and urgency.
        
        Args:
            base_size: Base size for the node
            urgency_multiplier: Multipliers for different urgency levels
        
        Returns:
            Calculated size for the node
        """
        if urgency_multiplier is None:
            urgency_multiplier = {
                UrgencyLevel.LOW: 0.8,
                UrgencyLevel.MEDIUM: 1.0,
                UrgencyLevel.HIGH: 1.3,
            }
        
        # Base size calculation based on label length
        label_factor = 0.8 + min(1.0, len(self.label) / 30.0)
        urgency_factor = urgency_multiplier.get(self.urgency, 1.0)
        
        return base_size * label_factor * urgency_factor
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "position": self.position.to_dict(),
            "urgency": self.urgency.value,
            "tag": self.tag,
            "parent_id": self.parent_id,
            "edge_type": self.edge_type.value,
            "size": self.size,
            "color": self.color,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Create Node from dictionary representation."""
        return cls(
            id=int(data["id"]),
            label=str(data["label"]),
            description=str(data.get("description", "")),
            position=Position.from_dict(data.get("position", {"x": 0.0, "y": 0.0})),
            urgency=UrgencyLevel(data.get("urgency", UrgencyLevel.MEDIUM.value)),
            tag=str(data.get("tag", "")),
            parent_id=int(data["parent_id"]) if data.get("parent_id") is not None else None,
            edge_type=EdgeType(data.get("edge_type", EdgeType.DEFAULT.value)),
            size=float(data.get("size", 20.0)),
            color=str(data.get("color", "#EEEEEE")),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
        )


@dataclass
class MindMapSettings:
    """Settings for the mind map visualization and behavior."""
    
    theme: str = "default"
    canvas_expanded: bool = False
    edge_length: int = 100
    spring_strength: float = 0.5
    size_multiplier: float = 1.0
    color_mode: str = "urgency"  # 'urgency' or 'tag'
    custom_tags: List[str] = field(default_factory=list)
    custom_colors: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary representation."""
        return {
            "theme": self.theme,
            "canvas_expanded": self.canvas_expanded,
            "edge_length": self.edge_length,
            "spring_strength": self.spring_strength,
            "size_multiplier": self.size_multiplier,
            "color_mode": self.color_mode,
            "custom_tags": self.custom_tags,
            "custom_colors": self.custom_colors,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MindMapSettings':
        """Create MindMapSettings from dictionary representation."""
        return cls(
            theme=data.get("theme", "default"),
            canvas_expanded=data.get("canvas_expanded", False),
            edge_length=data.get("edge_length", 100),
            spring_strength=data.get("spring_strength", 0.5),
            size_multiplier=data.get("size_multiplier", 1.0),
            color_mode=data.get("color_mode", "urgency"),
            custom_tags=data.get("custom_tags", []),
            custom_colors=data.get("custom_colors", {}),
        )


@dataclass
class MindMapMetadata:
    """Metadata for the mind map."""
    
    version: str = "2.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    node_count: int = 0
    backup_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation."""
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "node_count": self.node_count,
            "backup_count": self.backup_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MindMapMetadata':
        """Create MindMapMetadata from dictionary representation."""
        return cls(
            version=data.get("version", "2.0.0"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_modified=datetime.fromisoformat(data.get("last_modified", datetime.now().isoformat())),
            node_count=data.get("node_count", 0),
            backup_count=data.get("backup_count", 0),
        )


@dataclass
class MindMapData:
    """Aggregate root for mind map data."""
    
    nodes: List[Node] = field(default_factory=list)
    central_node_id: Optional[int] = None
    settings: MindMapSettings = field(default_factory=MindMapSettings)
    metadata: MindMapMetadata = field(default_factory=MindMapMetadata)
    
    def __post_init__(self):
        """Update metadata after initialization."""
        self.metadata.node_count = len(self.nodes)
        self.metadata.last_modified = datetime.now()
    
    def add_node(self, node: Node) -> 'MindMapData':
        """Add a node to the mind map."""
        if self.find_node_by_id(node.id) is not None:
            raise ValidationError(f"Node with id {node.id} already exists")
        
        new_nodes = self.nodes + [node]
        return self._update(nodes=new_nodes)
    
    def update_node(self, node: Node) -> 'MindMapData':
        """Update an existing node in the mind map."""
        existing_node = self.find_node_by_id(node.id)
        if existing_node is None:
            raise ValidationError(f"Node with id {node.id} not found")
        
        new_nodes = [node if n.id == node.id else n for n in self.nodes]
        return self._update(nodes=new_nodes)
    
    def remove_node(self, node_id: int) -> 'MindMapData':
        """Remove a node and all its descendants from the mind map."""
        descendants = self.get_descendants(node_id)
        descendants.add(node_id)  # Include the node itself
        
        new_nodes = [n for n in self.nodes if n.id not in descendants]
        new_central_id = self.central_node_id if self.central_node_id not in descendants else None
        
        return self._update(nodes=new_nodes, central_node_id=new_central_id)
    
    def find_node_by_id(self, node_id: int) -> Optional[Node]:
        """Find a node by its ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_children(self, parent_id: int) -> List[Node]:
        """Get all direct children of a node."""
        return [node for node in self.nodes if node.parent_id == parent_id]
    
    def get_descendants(self, node_id: int) -> Set[int]:
        """Get all descendants of a node (recursive)."""
        descendants = set()
        children = self.get_children(node_id)
        
        for child in children:
            descendants.add(child.id)
            descendants.update(self.get_descendants(child.id))
        
        return descendants
    
    def get_root_nodes(self) -> List[Node]:
        """Get all nodes that have no parent."""
        return [node for node in self.nodes if node.parent_id is None]
    
    def validate_relationships(self) -> List[ValidationError]:
        """Validate all parent-child relationships in the mind map."""
        errors = []
        
        for node in self.nodes:
            if node.parent_id is not None:
                parent = self.find_node_by_id(node.parent_id)
                if parent is None:
                    errors.append(ValidationError(
                        f"Node {node.id} has non-existent parent {node.parent_id}",
                        "parent_id"
                    ))
                elif self._would_create_cycle(node.id, node.parent_id):
                    errors.append(ValidationError(
                        f"Node {node.id} with parent {node.parent_id} would create a cycle",
                        "parent_id"
                    ))
        
        return errors
    
    def _would_create_cycle(self, child_id: int, parent_id: int) -> bool:
        """Check if setting parent_id as parent of child_id would create a cycle."""
        if child_id == parent_id:
            return True
        
        visited = set()
        current_id = parent_id
        
        while current_id is not None:
            if current_id == child_id:
                return True
            if current_id in visited:
                return True  # Already found a cycle
            
            visited.add(current_id)
            parent_node = self.find_node_by_id(current_id)
            current_id = parent_node.parent_id if parent_node else None
        
        return False
    
    def _update(self, **kwargs) -> 'MindMapData':
        """Create a new MindMapData with updated fields."""
        updated_data = {
            'nodes': self.nodes,
            'central_node_id': self.central_node_id,
            'settings': self.settings,
            'metadata': self.metadata,
        }
        updated_data.update(kwargs)
        
        # Update metadata
        if 'nodes' in kwargs:
            updated_data['metadata'] = MindMapMetadata(
                version=self.metadata.version,
                created_at=self.metadata.created_at,
                last_modified=datetime.now(),
                node_count=len(updated_data['nodes']),
                backup_count=self.metadata.backup_count,
            )
        
        return MindMapData(**updated_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mind map data to dictionary representation."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "central_node_id": self.central_node_id,
            "settings": self.settings.to_dict(),
            "metadata": self.metadata.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MindMapData':
        """Create MindMapData from dictionary representation."""
        # Handle backward compatibility: convert old 'ideas' format to new 'nodes' format
        node_data_list = data.get("nodes", [])
        
        # If no 'nodes' key but 'ideas' exists, convert from old format
        if not node_data_list and "ideas" in data:
            node_data_list = []
            for idea in data["ideas"]:
                # Convert old idea format to new node format
                node_dict = {
                    "id": idea["id"],
                    "label": idea["label"],
                    "description": idea.get("description", ""),
                    "position": {
                        "x": idea.get("x", 0.0),
                        "y": idea.get("y", 0.0)
                    },
                    "urgency": idea.get("urgency", "medium"),
                    "tag": idea.get("tag", ""),
                    "parent_id": idea.get("parent"),
                    "edge_type": idea.get("edge_type", "default"),
                    "size": idea.get("size", 20.0),
                    "color": idea.get("color", "#EEEEEE"),
                    "created_at": idea.get("created_at", datetime.now().isoformat()),
                    "updated_at": idea.get("updated_at", datetime.now().isoformat()),
                }
                node_data_list.append(node_dict)
        
        nodes = [Node.from_dict(node_data) for node_data in node_data_list]
        settings = MindMapSettings.from_dict(data.get("settings", {}))
        metadata = MindMapMetadata.from_dict(data.get("metadata", {}))
        
        # Handle central node ID from old format
        central_node_id = data.get("central_node_id")
        if central_node_id is None and "central" in data:
            central_node_id = data["central"]
        
        return cls(
            nodes=nodes,
            central_node_id=central_node_id,
            settings=settings,
            metadata=metadata,
        )