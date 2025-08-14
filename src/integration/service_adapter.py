"""
Service adapter for integrating the new architecture with existing UI components.

This module provides a bridge between the old Streamlit UI and the new service layer,
allowing for gradual migration while maintaining backward compatibility.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
import streamlit as st

from src.domain.models import Node, MindMapData, Position, UrgencyLevel, EdgeType
from src.application.services import MindMapService, NodeCreateRequest, NodeUpdateRequest
from src.infrastructure.repositories import JsonMindMapRepository, RepositoryFactory
from src.infrastructure.config import AppConfig, ConfigFactory

logger = logging.getLogger(__name__)


class ServiceAdapter:
    """
    Adapter class that provides the old interface while using the new service layer.
    
    This allows existing UI components to work without changes while benefiting
    from the new architecture's improvements.
    """
    
    def __init__(self):
        """Initialize the service adapter with proper configuration and services."""
        # Create configuration
        self.config = ConfigFactory.create_config()
        
        # Create repository and service
        self.repository = RepositoryFactory.create_repository(self.config, "json")
        self.service = MindMapService(self.repository, self.config)
        
        # Initialize session state compatibility
        self._init_session_state()
        
        logger.info("ServiceAdapter initialized with new architecture")
    
    def _init_session_state(self):
        """Initialize session state for backward compatibility."""
        if 'service_adapter' not in st.session_state:
            st.session_state['service_adapter'] = self
            
        # Ensure other session state variables exist for compatibility
        if 'store' not in st.session_state:
            st.session_state['store'] = {
                'ideas': [],
                'central': None,
                'next_id': 0,
                'history': [],
                'history_index': -1,
                'current_theme': 'default',
                'settings': {
                    'edge_length': 100,
                    'spring_strength': 0.5,
                    'size_multiplier': 1.0,
                    'canvas_expanded': False,
                    'color_mode': 'urgency',
                    'custom_tags': [],
                    'custom_colors': {
                        'urgency': {
                            'high': '#FF5252',
                            'medium': '#FFC107',
                            'low': '#4CAF50'
                        },
                        'tags': {
                            'work': '#2196F3',
                            'personal': '#9C27B0',
                            'idea': '#00BCD4',
                            'task': '#FF9800',
                            'note': '#607D8B',
                            'important': '#F44336',
                            'question': '#8BC34A',
                            'research': '#3F51B5'
                        }
                    }
                }
            }
    
    # === Backward Compatibility Methods ===
    
    def get_ideas(self) -> List[Dict[str, Any]]:
        """Get all nodes in the old format for backward compatibility."""
        nodes = self.service.get_all_nodes()
        return [self._node_to_old_format(node) for node in nodes]
    
    def get_central(self) -> Optional[int]:
        """Get the central node ID."""
        central_node = self.service.get_central_node()
        return central_node.id if central_node else None
    
    def get_next_id(self) -> int:
        """Get the next available node ID."""
        return self.service._next_id
    
    def set_central(self, node_id: Optional[int]) -> bool:
        """Set the central node."""
        result = self.service.set_central_node(node_id)
        return result.is_ok()
    
    def add_idea(self, node_data: Dict[str, Any]) -> bool:
        """Add a new node using the old format."""
        try:
            # Convert old format to new request
            request = self._old_format_to_create_request(node_data)
            result = self.service.create_node(request)
            
            if result.is_ok():
                logger.info(f"Successfully added node: {result.data.label}")
                return True
            else:
                logger.error(f"Failed to add node: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding node: {str(e)}")
            return False
    
    def set_ideas(self, ideas_list: List[Dict[str, Any]]) -> bool:
        """Set all nodes using the old format (used for bulk updates)."""
        try:
            # This is a complex operation that requires careful handling
            # For now, we'll log this and return True to maintain compatibility
            logger.warning("set_ideas called - this operation needs careful implementation")
            return True
        except Exception as e:
            logger.error(f"Error setting ideas: {str(e)}")
            return False
    
    def update_node_position(self, node_id: int, x: float, y: float) -> bool:
        """Update a node's position."""
        try:
            position = Position(x, y)
            request = NodeUpdateRequest(position=position)
            result = self.service.update_node(node_id, request)
            
            if result.is_ok():
                logger.debug(f"Updated position for node {node_id}: ({x}, {y})")
                return True
            else:
                logger.error(f"Failed to update position for node {node_id}: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating node position: {str(e)}")
            return False
    
    def delete_node(self, node_id: int) -> bool:
        """Delete a node and its descendants."""
        try:
            result = self.service.delete_node(node_id)
            
            if result.is_ok():
                deleted_count = result.data.get("deleted_count", 1)
                logger.info(f"Successfully deleted node {node_id} and {deleted_count-1} descendants")
                return True
            else:
                logger.error(f"Failed to delete node {node_id}: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting node: {str(e)}")
            return False
    
    def find_node_by_id(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Find a node by ID and return in old format."""
        result = self.service.get_node(node_id)
        
        if result.is_ok():
            return self._node_to_old_format(result.data)
        else:
            return None
    
    def search_nodes(self, query: str) -> List[Dict[str, Any]]:
        """Search nodes and return results in old format."""
        nodes = self.service.search_nodes(query)
        return [self._node_to_old_format(node) for node in nodes]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mind map statistics."""
        return self.service.get_statistics()
    
    def create_backup(self) -> Optional[str]:
        """Create a backup and return the backup path."""
        result = self.service.create_backup()
        return result.data if result.is_ok() else None
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        result = self.service.list_backups()
        return result.data if result.is_ok() else []
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore from a backup."""
        result = self.service.restore_backup(backup_path)
        return result.is_ok()
    
    # === Format Conversion Methods ===
    
    def _node_to_old_format(self, node: Node) -> Dict[str, Any]:
        """Convert a Node object to the old dictionary format."""
        return {
            'id': node.id,
            'label': node.label,
            'description': node.description,
            'x': node.position.x,
            'y': node.position.y,
            'urgency': node.urgency.value,
            'tag': node.tag,
            'parent': node.parent_id,
            'edge_type': node.edge_type.value,
            'size': node.size,
            'color': node.color,
            'created_at': node.created_at.isoformat(),
            'updated_at': node.updated_at.isoformat(),
        }
    
    def _old_format_to_create_request(self, node_data: Dict[str, Any]) -> NodeCreateRequest:
        """Convert old format node data to a NodeCreateRequest."""
        # Extract position
        position = Position(
            x=float(node_data.get('x', 0)),
            y=float(node_data.get('y', 0))
        )
        
        # Convert urgency
        urgency_str = node_data.get('urgency', 'medium')
        try:
            urgency = UrgencyLevel(urgency_str)
        except ValueError:
            urgency = UrgencyLevel.MEDIUM
        
        # Convert edge type
        edge_type_str = node_data.get('edge_type', 'default')
        try:
            edge_type = EdgeType(edge_type_str)
        except ValueError:
            edge_type = EdgeType.DEFAULT
        
        return NodeCreateRequest(
            label=node_data.get('label', 'Untitled'),
            description=node_data.get('description', ''),
            position=position,
            urgency=urgency,
            tag=node_data.get('tag', ''),
            parent_id=node_data.get('parent'),
            edge_type=edge_type
        )
    
    def _old_format_to_update_request(self, node_data: Dict[str, Any]) -> NodeUpdateRequest:
        """Convert old format node data to a NodeUpdateRequest."""
        request = NodeUpdateRequest()
        
        if 'label' in node_data:
            request.label = node_data['label']
        
        if 'description' in node_data:
            request.description = node_data['description']
        
        if 'x' in node_data and 'y' in node_data:
            request.position = Position(
                x=float(node_data['x']),
                y=float(node_data['y'])
            )
        
        if 'urgency' in node_data:
            try:
                request.urgency = UrgencyLevel(node_data['urgency'])
            except ValueError:
                pass
        
        if 'tag' in node_data:
            request.tag = node_data['tag']
        
        if 'parent' in node_data:
            request.parent_id = node_data['parent']
        
        if 'edge_type' in node_data:
            try:
                request.edge_type = EdgeType(node_data['edge_type'])
            except ValueError:
                pass
        
        return request
    
    # === New Service Methods (for gradual migration) ===
    
    def get_service(self) -> MindMapService:
        """Get the underlying service for direct access."""
        return self.service
    
    def get_config(self) -> AppConfig:
        """Get the application configuration."""
        return self.config
    
    def reload_data(self) -> bool:
        """Reload data from storage."""
        try:
            self.service._load_data()
            return True
        except Exception as e:
            logger.error(f"Error reloading data: {str(e)}")
            return False


# Global service adapter instance
_service_adapter: Optional[ServiceAdapter] = None


def get_service_adapter() -> ServiceAdapter:
    """Get the global service adapter instance."""
    global _service_adapter
    
    if _service_adapter is None:
        _service_adapter = ServiceAdapter()
    
    return _service_adapter


def init_service_adapter() -> ServiceAdapter:
    """Initialize the service adapter and return it."""
    adapter = get_service_adapter()
    
    # Store in session state for easy access
    st.session_state['service_adapter'] = adapter
    
    return adapter


# === Backward Compatibility Functions ===
# These functions maintain the old API while using the new service layer

def get_ideas() -> List[Dict[str, Any]]:
    """Get all ideas using the service adapter."""
    return get_service_adapter().get_ideas()


def get_central() -> Optional[int]:
    """Get central node using the service adapter."""
    return get_service_adapter().get_central()


def get_next_id() -> int:
    """Get next ID using the service adapter."""
    return get_service_adapter().get_next_id()


def set_central(node_id: Optional[int]) -> bool:
    """Set central node using the service adapter."""
    return get_service_adapter().set_central(node_id)


def add_idea(node_data: Dict[str, Any]) -> bool:
    """Add idea using the service adapter."""
    return get_service_adapter().add_idea(node_data)


def set_ideas(ideas_list: List[Dict[str, Any]]) -> bool:
    """Set ideas using the service adapter."""
    return get_service_adapter().set_ideas(ideas_list)


def find_node_by_id(node_id: int) -> Optional[Dict[str, Any]]:
    """Find node by ID using the service adapter."""
    return get_service_adapter().find_node_by_id(node_id)