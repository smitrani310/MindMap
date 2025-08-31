"""
Application services for the Enhanced Mind Map application.

This module contains the service layer that orchestrates business logic
and coordinates between the domain models and infrastructure.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from functools import lru_cache

from src.domain.models import (
    Node, MindMapData, Position, UrgencyLevel, EdgeType, 
    ValidationError, MindMapSettings, MindMapMetadata
)
from src.infrastructure.repositories import MindMapRepository, Result
from src.infrastructure.config import AppConfig
from src.infrastructure.cache import (
    get_cache_manager, cached, cache_key_for_node, cache_key_for_search,
    invalidate_node_cache, invalidate_search_cache, invalidate_computation_cache
)
from src.infrastructure.performance import timed, performance_context
from src.infrastructure.events import EventType, publish_event, create_node_event


class ServiceError(Exception):
    """Base exception for service layer operations."""
    
    def __init__(self, message: str, operation: str, original_error: Optional[Exception] = None):
        self.message = message
        self.operation = operation
        self.original_error = original_error
        super().__init__(message)


class NodeCreateRequest:
    """Request object for creating a new node."""
    
    def __init__(
        self,
        label: str,
        description: str = "",
        position: Optional[Position] = None,
        urgency: UrgencyLevel = UrgencyLevel.MEDIUM,
        tag: str = "",
        parent_id: Optional[int] = None,
        edge_type: EdgeType = EdgeType.DEFAULT,
    ):
        self.label = label
        self.description = description
        self.position = position or Position.origin()
        self.urgency = urgency
        self.tag = tag
        self.parent_id = parent_id
        self.edge_type = edge_type


class NodeUpdateRequest:
    """Request object for updating an existing node."""
    
    def __init__(
        self,
        label: Optional[str] = None,
        description: Optional[str] = None,
        position: Optional[Position] = None,
        urgency: Optional[UrgencyLevel] = None,
        tag: Optional[str] = None,
        parent_id: Optional[int] = None,
        edge_type: Optional[EdgeType] = None,
    ):
        self.label = label
        self.description = description
        self.position = position
        self.urgency = urgency
        self.tag = tag
        self.parent_id = parent_id
        self.edge_type = edge_type


class MindMapService:
    """Core service for mind map operations."""
    
    def __init__(self, repository: MindMapRepository, config: AppConfig):
        self.repository = repository
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._current_data: Optional[MindMapData] = None
        self._next_id = 1
        
        # Initialize cache manager
        self.cache_manager = get_cache_manager()
        
        # Load initial data
        self._load_data()
    
    def _load_data(self) -> None:
        """Load data from repository."""
        result = self.repository.load()
        if result.is_ok():
            self._current_data = result.data
            # Update next_id based on existing nodes
            if self._current_data.nodes:
                self._next_id = max(node.id for node in self._current_data.nodes) + 1
        else:
            self.logger.error(f"Failed to load data: {result.error}")
            self._current_data = MindMapData()
    
    def _save_data(self) -> Result:
        """Save current data to repository."""
        if self._current_data is None:
            return Result.fail("No data to save")
        
        result = self.repository.save(self._current_data)
        if result.is_ok():
            self.logger.debug("Data saved successfully")
        else:
            self.logger.error(f"Failed to save data: {result.error}")
        
        return result
    
    def _get_next_id(self) -> int:
        """Get the next available node ID."""
        current_id = self._next_id
        self._next_id += 1
        return current_id
    
    def get_mindmap_data(self) -> MindMapData:
        """Get the current mind map data."""
        if self._current_data is None:
            self._load_data()
        return self._current_data
    
    @timed(operation_name="mindmap_service.create_node")
    def create_node(self, request: NodeCreateRequest) -> Result:
        """
        Create a new node.
        
        Args:
            request: NodeCreateRequest with node details
            
        Returns:
            Result containing the created Node or error
        """
        try:
            # Validate parent exists if specified
            if request.parent_id is not None:
                parent_node = self._current_data.find_node_by_id(request.parent_id)
                if parent_node is None:
                    return Result.fail(f"Parent node with id {request.parent_id} not found")
            
            # Create new node
            node = Node(
                id=self._get_next_id(),
                label=request.label,
                description=request.description,
                position=request.position,
                urgency=request.urgency,
                tag=request.tag,
                parent_id=request.parent_id,
                edge_type=request.edge_type,
            )
            
            # Validate the node
            validation_errors = node.validate()
            if validation_errors:
                error_messages = [error.message for error in validation_errors]
                return Result.fail(f"Node validation failed: {'; '.join(error_messages)}")
            
            # Calculate size based on configuration
            node.size = node.calculate_size()
            
            # Add to mind map
            self._current_data = self._current_data.add_node(node)
            
            # Save changes
            save_result = self._save_data()
            if not save_result.is_ok():
                return save_result
            
            # Invalidate caches
            invalidate_search_cache()
            invalidate_computation_cache()
            
            # Publish node created event
            publish_event(
                EventType.NODE_CREATED,
                source="MindMapService",
                data={
                    'node_id': node.id,
                    'label': node.label,
                    'position': {'x': node.position.x, 'y': node.position.y},
                    'urgency': node.urgency.value,
                    'tag': node.tag
                }
            )
            
            self.logger.info(f"Created node {node.id}: {node.label}")
            return Result.ok(node)
            
        except ValidationError as e:
            error_msg = f"Validation error creating node: {e.message}"
            self.logger.warning(error_msg)
            return Result.fail(error_msg)
        
        except Exception as e:
            error_msg = f"Error creating node: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    @timed(operation_name="mindmap_service.update_node")
    def update_node(self, node_id: int, request: NodeUpdateRequest) -> Result:
        """
        Update an existing node.
        
        Args:
            node_id: ID of the node to update
            request: NodeUpdateRequest with updated values
            
        Returns:
            Result containing the updated Node or error
        """
        try:
            # Find existing node
            existing_node = self._current_data.find_node_by_id(node_id)
            if existing_node is None:
                return Result.fail(f"Node with id {node_id} not found")
            
            # Create updated node
            updated_node = existing_node
            
            if request.label is not None:
                updated_node = updated_node.update_label(request.label)
            
            if request.description is not None:
                updated_node = updated_node.update_description(request.description)
            
            if request.position is not None:
                updated_node = updated_node.update_position(request.position)
            
            if request.urgency is not None:
                updated_node = updated_node.update_urgency(request.urgency)
            
            if request.tag is not None:
                updated_node = updated_node.update_tag(request.tag)
            
            if request.parent_id is not None or request.edge_type is not None:
                parent_id = request.parent_id if request.parent_id is not None else existing_node.parent_id
                edge_type = request.edge_type if request.edge_type is not None else existing_node.edge_type
                
                # Validate parent exists if specified
                if parent_id is not None:
                    parent_node = self._current_data.find_node_by_id(parent_id)
                    if parent_node is None:
                        return Result.fail(f"Parent node with id {parent_id} not found")
                    
                    # Check for circular reference
                    if self._current_data._would_create_cycle(node_id, parent_id):
                        return Result.fail("Cannot create circular reference")
                
                updated_node = updated_node.set_parent(parent_id, edge_type)
            
            # Recalculate size
            updated_node.size = updated_node.calculate_size()
            
            # Update in mind map
            self._current_data = self._current_data.update_node(updated_node)
            
            # Save changes
            save_result = self._save_data()
            if not save_result.is_ok():
                return save_result
            
            # Invalidate caches
            invalidate_node_cache(node_id)
            invalidate_search_cache()
            invalidate_computation_cache()
            
            # Determine what fields were updated
            updated_fields = []
            if request.label is not None:
                updated_fields.append('label')
            if request.description is not None:
                updated_fields.append('description')
            if request.position is not None:
                updated_fields.append('position')
            if request.urgency is not None:
                updated_fields.append('urgency')
            if request.tag is not None:
                updated_fields.append('tag')
            if request.parent_id is not None or request.edge_type is not None:
                updated_fields.append('parent')
            
            # Publish node updated event
            publish_event(
                EventType.NODE_UPDATED,
                source="MindMapService",
                data={
                    'node_id': node_id,
                    'updated_fields': updated_fields,
                    'label': updated_node.label,
                    'position': {'x': updated_node.position.x, 'y': updated_node.position.y},
                    'urgency': updated_node.urgency.value,
                    'tag': updated_node.tag
                }
            )
            
            self.logger.info(f"Updated node {node_id}")
            return Result.ok(updated_node)
            
        except ValidationError as e:
            error_msg = f"Validation error updating node: {e.message}"
            self.logger.warning(error_msg)
            return Result.fail(error_msg)
        
        except Exception as e:
            error_msg = f"Error updating node: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    @timed(operation_name="mindmap_service.delete_node")
    def delete_node(self, node_id: int) -> Result:
        """
        Delete a node and all its descendants.
        
        Args:
            node_id: ID of the node to delete
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Check if node exists
            node = self._current_data.find_node_by_id(node_id)
            if node is None:
                return Result.fail(f"Node with id {node_id} not found")
            
            # Get descendants for logging
            descendants = self._current_data.get_descendants(node_id)
            
            # Remove node and descendants
            self._current_data = self._current_data.remove_node(node_id)
            
            # Save changes
            save_result = self._save_data()
            if not save_result.is_ok():
                return save_result
            
            # Invalidate caches for all affected nodes
            for affected_id in descendants:
                invalidate_node_cache(affected_id)
            invalidate_node_cache(node_id)
            invalidate_search_cache()
            invalidate_computation_cache()
            
            # Publish node deleted event
            publish_event(
                EventType.NODE_DELETED,
                source="MindMapService",
                data={
                    'node_id': node_id,
                    'deleted_count': len(descendants) + 1,
                    'label': node.label,
                    'descendants': descendants
                }
            )
            
            self.logger.info(f"Deleted node {node_id} and {len(descendants)} descendants")
            return Result.ok({"deleted_count": len(descendants) + 1})
            
        except Exception as e:
            error_msg = f"Error deleting node: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    def get_node(self, node_id: int) -> Result:
        """
        Get a node by ID.
        
        Args:
            node_id: ID of the node to retrieve
            
        Returns:
            Result containing the Node or error
        """
        node = self._current_data.find_node_by_id(node_id)
        if node is None:
            return Result.fail(f"Node with id {node_id} not found")
        
        return Result.ok(node)
    
    def get_all_nodes(self) -> List[Node]:
        """Get all nodes in the mind map."""
        return self._current_data.nodes
    
    def get_children(self, parent_id: int) -> List[Node]:
        """Get all direct children of a node."""
        return self._current_data.get_children(parent_id)
    
    def get_root_nodes(self) -> List[Node]:
        """Get all nodes that have no parent."""
        return self._current_data.get_root_nodes()
    
    def set_central_node(self, node_id: Optional[int]) -> Result:
        """
        Set the central node of the mind map.
        
        Args:
            node_id: ID of the node to set as central, or None to clear
            
        Returns:
            Result indicating success or failure
        """
        try:
            if node_id is not None:
                # Validate node exists
                node = self._current_data.find_node_by_id(node_id)
                if node is None:
                    return Result.fail(f"Node with id {node_id} not found")
            
            # Update central node
            self._current_data.central_node_id = node_id
            
            # Save changes
            save_result = self._save_data()
            if not save_result.is_ok():
                return save_result
            
            self.logger.info(f"Set central node to {node_id}")
            return Result.ok()
            
        except Exception as e:
            error_msg = f"Error setting central node: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    def get_central_node(self) -> Optional[Node]:
        """Get the current central node."""
        if self._current_data.central_node_id is None:
            return None
        return self._current_data.find_node_by_id(self._current_data.central_node_id)
    
    def update_settings(self, settings: MindMapSettings) -> Result:
        """
        Update mind map settings.
        
        Args:
            settings: New settings to apply
            
        Returns:
            Result indicating success or failure
        """
        try:
            self._current_data.settings = settings
            
            # Save changes
            save_result = self._save_data()
            if not save_result.is_ok():
                return save_result
            
            self.logger.info("Updated mind map settings")
            return Result.ok()
            
        except Exception as e:
            error_msg = f"Error updating settings: {str(e)}"
            self.logger.error(error_msg)
            return Result.fail(error_msg)
    
    def get_settings(self) -> MindMapSettings:
        """Get current mind map settings."""
        return self._current_data.settings
    
    @timed(operation_name="mindmap_service.search_nodes")
    def search_nodes(self, query: str, search_in_description: bool = True) -> List[Node]:
        """
        Search for nodes containing the query string.
        
        Args:
            query: Search query
            search_in_description: Whether to search in node descriptions
            
        Returns:
            List of nodes matching the query
        """
        if not query.strip():
            return []
        
        # Generate cache key for this search
        cache_key = cache_key_for_search(query, {'search_in_description': search_in_description})
        
        # Try to get from cache
        search_cache = self.cache_manager.get_cache('search')
        if search_cache:
            cached_result = search_cache.get(cache_key)
            if cached_result is not None:
                self.logger.debug(f"Search cache hit for query: {query}")
                return cached_result
        
        # Perform search
        query_lower = query.lower()
        matching_nodes = []
        
        for node in self._current_data.nodes:
            # Search in label
            if query_lower in node.label.lower():
                matching_nodes.append(node)
                continue
            
            # Search in description if enabled
            if search_in_description and query_lower in node.description.lower():
                matching_nodes.append(node)
                continue
            
            # Search in tag
            if query_lower in node.tag.lower():
                matching_nodes.append(node)
        
        # Cache the result
        if search_cache:
            search_cache.put(cache_key, matching_nodes, ttl=120)  # Cache for 2 minutes
            self.logger.debug(f"Cached search result for query: {query}")
        
        return matching_nodes
    
    def get_nodes_by_tag(self, tag: str) -> List[Node]:
        """Get all nodes with a specific tag."""
        return [node for node in self._current_data.nodes if node.tag == tag]
    
    def get_nodes_by_urgency(self, urgency: UrgencyLevel) -> List[Node]:
        """Get all nodes with a specific urgency level."""
        return [node for node in self._current_data.nodes if node.urgency == urgency]
    
    @timed(operation_name="mindmap_service.get_statistics")
    @cached(cache_name='computation', ttl=60)  # Cache for 1 minute
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the mind map."""
        nodes = self._current_data.nodes
        
        if not nodes:
            return {
                "total_nodes": 0,
                "root_nodes": 0,
                "max_depth": 0,
                "urgency_distribution": {},
                "tag_distribution": {},
            }
        
        # Calculate statistics
        root_nodes = len(self.get_root_nodes())
        
        urgency_counts = {}
        tag_counts = {}
        
        for node in nodes:
            # Count urgency levels
            urgency_counts[node.urgency.value] = urgency_counts.get(node.urgency.value, 0) + 1
            
            # Count tags
            if node.tag:
                tag_counts[node.tag] = tag_counts.get(node.tag, 0) + 1
        
        # Calculate max depth
        max_depth = self._calculate_max_depth()
        
        return {
            "total_nodes": len(nodes),
            "root_nodes": root_nodes,
            "max_depth": max_depth,
            "urgency_distribution": urgency_counts,
            "tag_distribution": tag_counts,
            "last_modified": self._current_data.metadata.last_modified.isoformat(),
        }
    
    def _calculate_max_depth(self) -> int:
        """Calculate the maximum depth of the mind map tree."""
        def get_depth(node_id: int, visited: Set[int]) -> int:
            if node_id in visited:
                return 0  # Avoid infinite recursion in case of cycles
            
            visited.add(node_id)
            children = self.get_children(node_id)
            
            if not children:
                return 1
            
            max_child_depth = max(get_depth(child.id, visited.copy()) for child in children)
            return 1 + max_child_depth
        
        root_nodes = self.get_root_nodes()
        if not root_nodes:
            return 0
        
        return max(get_depth(root.id, set()) for root in root_nodes)
    
    def create_backup(self) -> Result:
        """Create a backup of the current data."""
        return self.repository.backup()
    
    def list_backups(self) -> Result:
        """List available backups."""
        return self.repository.list_backups()
    
    def restore_backup(self, backup_path: str) -> Result:
        """
        Restore data from a backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            Result indicating success or failure
        """
        result = self.repository.restore(backup_path)
        if result.is_ok():
            # Reload data after restore
            self._load_data()
            self.logger.info(f"Restored data from backup: {backup_path}")
        
        return result