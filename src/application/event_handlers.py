"""
Event handlers for the Enhanced Mind Map application.

This module provides specialized event handlers for different domains:
- NodeEventHandler: Handles node-related events
- UIEventHandler: Handles user interface events  
- SystemEventHandler: Handles system events
- Event handler registration and management
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Set
from datetime import datetime

from src.infrastructure.event_system import (
    Event, EventType, EventBus, get_event_bus, event_handler
)
from src.infrastructure.domain_events import (
    NodeEvent, NodeCreatedEvent, NodeUpdatedEvent, NodeDeletedEvent,
    UIEvent, SystemEvent, DataEvent, PerformanceEvent
)


class BaseEventHandler(ABC):
    """Abstract base class for event handlers."""
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(f"{__name__}.{name}")
        self.handled_events_count = 0
        self.last_handled_at: Optional[datetime] = None
        self.error_count = 0
        self.subscription_ids: List[str] = []
    
    @abstractmethod
    def get_handled_event_types(self) -> Set[EventType]:
        """Return the set of event types this handler processes."""
        pass
    
    @abstractmethod
    def handle_event(self, event: Event) -> None:
        """Handle a specific event."""
        pass
    
    def register(self, event_bus: Optional[EventBus] = None) -> None:
        """Register this handler with the event bus."""
        bus = event_bus or get_event_bus()
        
        for event_type in self.get_handled_event_types():
            subscription_id = bus.subscribe(
                event_type,
                self._handle_event_wrapper,
                subscription_id=f"{self.name}_{event_type.value}",
                priority=self.get_priority_for_event_type(event_type)
            )
            self.subscription_ids.append(subscription_id)
        
        self.logger.info(f"Registered {self.name} for {len(self.subscription_ids)} event types")
    
    def unregister(self, event_bus: Optional[EventBus] = None) -> None:
        """Unregister this handler from the event bus."""
        bus = event_bus or get_event_bus()
        
        for subscription_id in self.subscription_ids:
            bus.unsubscribe(subscription_id)
        
        self.subscription_ids.clear()
        self.logger.info(f"Unregistered {self.name}")
    
    def get_priority_for_event_type(self, event_type: EventType) -> int:
        """Get the priority for a specific event type. Override in subclasses."""
        return 5  # Default priority
    
    def _handle_event_wrapper(self, event: Event) -> None:
        """Wrapper that adds common handling logic."""
        try:
            self.logger.debug(
                f"Handling event {event.event_type.value}",
                extra={
                    'event_id': event.event_id,
                    'handler': self.name,
                    'correlation_id': event.metadata.correlation_id
                }
            )
            
            self.handle_event(event)
            
            self.handled_events_count += 1
            self.last_handled_at = datetime.now()
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(
                f"Error handling event {event.event_type.value}: {e}",
                extra={
                    'event_id': event.event_id,
                    'handler': self.name,
                    'error': str(e)
                },
                exc_info=True
            )
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            'name': self.name,
            'handled_events_count': self.handled_events_count,
            'error_count': self.error_count,
            'last_handled_at': self.last_handled_at.isoformat() if self.last_handled_at else None,
            'subscription_count': len(self.subscription_ids),
            'handled_event_types': [et.value for et in self.get_handled_event_types()]
        }


class NodeEventHandler(BaseEventHandler):
    """Handler for node-related events."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("NodeEventHandler", logger)
        self.node_cache: Dict[int, Dict[str, Any]] = {}
        self.node_relationships: Dict[int, Set[int]] = {}  # parent_id -> set of child_ids
        self.node_creation_count = 0
        self.node_update_count = 0
        self.node_deletion_count = 0
    
    def get_handled_event_types(self) -> Set[EventType]:
        """Return node-related event types."""
        return {
            EventType.NODE_CREATED,
            EventType.NODE_UPDATED,
            EventType.NODE_DELETED,
            EventType.NODE_MOVED,
            EventType.NODE_PARENT_CHANGED
        }
    
    def get_priority_for_event_type(self, event_type: EventType) -> int:
        """Get priority for node events."""
        priority_map = {
            EventType.NODE_CREATED: 10,  # High priority for creation
            EventType.NODE_DELETED: 10,  # High priority for deletion
            EventType.NODE_PARENT_CHANGED: 8,  # High priority for structure changes
            EventType.NODE_UPDATED: 5,   # Normal priority for updates
            EventType.NODE_MOVED: 3      # Lower priority for position changes
        }
        return priority_map.get(event_type, 5)
    
    def handle_event(self, event: Event) -> None:
        """Handle node-related events."""
        if event.event_type == EventType.NODE_CREATED:
            self._handle_node_created(event)
        elif event.event_type == EventType.NODE_UPDATED:
            self._handle_node_updated(event)
        elif event.event_type == EventType.NODE_DELETED:
            self._handle_node_deleted(event)
        elif event.event_type == EventType.NODE_MOVED:
            self._handle_node_moved(event)
        elif event.event_type == EventType.NODE_PARENT_CHANGED:
            self._handle_node_parent_changed(event)
    
    def _handle_node_created(self, event: Event) -> None:
        """Handle node creation events."""
        node_id = event.data.get('node_id')
        if not node_id:
            self.logger.warning("Node created event missing node_id")
            return
        
        # Update local cache
        node_data = event.data.get('node_data', {})
        self.node_cache[node_id] = {
            'id': node_id,
            'title': node_data.get('title', ''),
            'content': node_data.get('content', ''),
            'parent_id': node_data.get('parent_id'),
            'position': node_data.get('position', {'x': 0, 'y': 0}),
            'created_at': event.timestamp.isoformat(),
            'updated_at': event.timestamp.isoformat()
        }
        
        # Update relationships
        parent_id = node_data.get('parent_id')
        if parent_id:
            if parent_id not in self.node_relationships:
                self.node_relationships[parent_id] = set()
            self.node_relationships[parent_id].add(node_id)
        
        self.node_creation_count += 1
        
        self.logger.info(
            f"Node created: {node_id} - '{node_data.get('title', 'Untitled')}'",
            extra={
                'node_id': node_id,
                'parent_id': parent_id,
                'event_id': event.event_id
            }
        )
        
        # Trigger dependent operations
        self._invalidate_related_caches(node_id)
        self._update_search_index(node_id, node_data)
    
    def _handle_node_updated(self, event: Event) -> None:
        """Handle node update events."""
        node_id = event.data.get('node_id')
        if not node_id:
            self.logger.warning("Node updated event missing node_id")
            return
        
        changes = event.data.get('node_data', {}).get('changes', {})
        old_values = event.data.get('node_data', {}).get('old_values', {})
        
        # Update local cache
        if node_id in self.node_cache:
            self.node_cache[node_id].update(changes)
            self.node_cache[node_id]['updated_at'] = event.timestamp.isoformat()
        
        self.node_update_count += 1
        
        self.logger.info(
            f"Node updated: {node_id} - Changes: {list(changes.keys())}",
            extra={
                'node_id': node_id,
                'changes': changes,
                'old_values': old_values,
                'event_id': event.event_id
            }
        )
        
        # Handle specific change types
        if 'title' in changes or 'content' in changes:
            self._update_search_index(node_id, changes)
        
        if 'parent_id' in changes:
            self._handle_parent_change(node_id, old_values.get('parent_id'), changes['parent_id'])
        
        self._invalidate_related_caches(node_id)
    
    def _handle_node_deleted(self, event: Event) -> None:
        """Handle node deletion events."""
        node_id = event.data.get('node_id')
        if not node_id:
            self.logger.warning("Node deleted event missing node_id")
            return
        
        deleted_node_data = event.data.get('node_data', {}).get('deleted_node_data', {})
        cascade_deleted = event.data.get('node_data', {}).get('cascade_deleted', [])
        
        # Remove from cache
        if node_id in self.node_cache:
            del self.node_cache[node_id]
        
        # Update relationships
        parent_id = deleted_node_data.get('parent_id')
        if parent_id and parent_id in self.node_relationships:
            self.node_relationships[parent_id].discard(node_id)
        
        # Remove as parent
        if node_id in self.node_relationships:
            del self.node_relationships[node_id]
        
        self.node_deletion_count += 1
        
        self.logger.info(
            f"Node deleted: {node_id} - Cascade deleted: {len(cascade_deleted)}",
            extra={
                'node_id': node_id,
                'cascade_deleted': cascade_deleted,
                'event_id': event.event_id
            }
        )
        
        # Clean up related data
        self._remove_from_search_index(node_id)
        self._invalidate_related_caches(node_id)
        
        # Handle cascade deletions
        for child_id in cascade_deleted:
            if child_id in self.node_cache:
                del self.node_cache[child_id]
            self._remove_from_search_index(child_id)
    
    def _handle_node_moved(self, event: Event) -> None:
        """Handle node movement events."""
        node_id = event.data.get('node_id')
        if not node_id:
            return
        
        old_position = event.data.get('node_data', {}).get('old_position', {})
        new_position = event.data.get('node_data', {}).get('new_position', {})
        
        # Update position in cache
        if node_id in self.node_cache:
            self.node_cache[node_id]['position'] = new_position
            self.node_cache[node_id]['updated_at'] = event.timestamp.isoformat()
        
        self.logger.debug(
            f"Node moved: {node_id} from {old_position} to {new_position}",
            extra={'node_id': node_id, 'event_id': event.event_id}
        )
    
    def _handle_node_parent_changed(self, event: Event) -> None:
        """Handle node parent change events."""
        node_id = event.data.get('node_id')
        old_parent_id = event.data.get('old_parent_id')
        new_parent_id = event.data.get('new_parent_id')
        
        self._handle_parent_change(node_id, old_parent_id, new_parent_id)
    
    def _handle_parent_change(self, node_id: int, old_parent_id: Optional[int], new_parent_id: Optional[int]) -> None:
        """Handle parent relationship changes."""
        # Remove from old parent
        if old_parent_id and old_parent_id in self.node_relationships:
            self.node_relationships[old_parent_id].discard(node_id)
        
        # Add to new parent
        if new_parent_id:
            if new_parent_id not in self.node_relationships:
                self.node_relationships[new_parent_id] = set()
            self.node_relationships[new_parent_id].add(node_id)
        
        # Update cache
        if node_id in self.node_cache:
            self.node_cache[node_id]['parent_id'] = new_parent_id
    
    def _invalidate_related_caches(self, node_id: int) -> None:
        """Invalidate caches related to a node."""
        # This would integrate with the cache system
        self.logger.debug(f"Invalidating caches for node {node_id}")
    
    def _update_search_index(self, node_id: int, node_data: Dict[str, Any]) -> None:
        """Update search index for a node."""
        # This would integrate with the search system
        self.logger.debug(f"Updating search index for node {node_id}")
    
    def _remove_from_search_index(self, node_id: int) -> None:
        """Remove node from search index."""
        # This would integrate with the search system
        self.logger.debug(f"Removing node {node_id} from search index")
    
    def get_node_stats(self) -> Dict[str, Any]:
        """Get node-specific statistics."""
        return {
            'total_nodes': len(self.node_cache),
            'nodes_created': self.node_creation_count,
            'nodes_updated': self.node_update_count,
            'nodes_deleted': self.node_deletion_count,
            'parent_child_relationships': len(self.node_relationships),
            'orphan_nodes': len([n for n in self.node_cache.values() if not n.get('parent_id')])
        }


class UIEventHandler(BaseEventHandler):
    """Handler for user interface events."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("UIEventHandler", logger)
        self.selected_nodes: Set[int] = set()
        self.current_zoom_level: float = 1.0
        self.current_center_position: Dict[str, float] = {'x': 0, 'y': 0}
        self.active_filters: Dict[str, Any] = {}
        self.ui_interaction_count = 0
        self.selection_history: List[Dict[str, Any]] = []
    
    def get_handled_event_types(self) -> Set[EventType]:
        """Return UI-related event types."""
        return {
            EventType.UI_NODE_SELECTED,
            EventType.UI_NODE_DESELECTED,
            EventType.UI_ZOOM_CHANGED,
            EventType.UI_VIEW_CHANGED,
            EventType.UI_FILTER_APPLIED
        }
    
    def get_priority_for_event_type(self, event_type: EventType) -> int:
        """Get priority for UI events."""
        priority_map = {
            EventType.UI_NODE_SELECTED: 7,    # High priority for selection
            EventType.UI_NODE_DESELECTED: 7,  # High priority for deselection
            EventType.UI_FILTER_APPLIED: 6,   # Medium-high for filtering
            EventType.UI_VIEW_CHANGED: 4,     # Medium priority for view changes
            EventType.UI_ZOOM_CHANGED: 3      # Lower priority for zoom
        }
        return priority_map.get(event_type, 5)
    
    def handle_event(self, event: Event) -> None:
        """Handle UI-related events."""
        self.ui_interaction_count += 1
        
        if event.event_type == EventType.UI_NODE_SELECTED:
            self._handle_node_selected(event)
        elif event.event_type == EventType.UI_NODE_DESELECTED:
            self._handle_node_deselected(event)
        elif event.event_type == EventType.UI_ZOOM_CHANGED:
            self._handle_zoom_changed(event)
        elif event.event_type == EventType.UI_VIEW_CHANGED:
            self._handle_view_changed(event)
        elif event.event_type == EventType.UI_FILTER_APPLIED:
            self._handle_filter_applied(event)
    
    def _handle_node_selected(self, event: Event) -> None:
        """Handle node selection events."""
        ui_data = event.data.get('ui_data', {})
        node_id = ui_data.get('node_id')
        selection_mode = ui_data.get('selection_mode', 'single')
        
        if node_id is None:
            return
        
        # Handle selection mode
        if selection_mode == 'single':
            self.selected_nodes.clear()
            self.selected_nodes.add(node_id)
        elif selection_mode == 'multi':
            self.selected_nodes.add(node_id)
        elif selection_mode == 'toggle':
            if node_id in self.selected_nodes:
                self.selected_nodes.remove(node_id)
            else:
                self.selected_nodes.add(node_id)
        
        # Record selection history
        self.selection_history.append({
            'action': 'select',
            'node_id': node_id,
            'selection_mode': selection_mode,
            'timestamp': event.timestamp.isoformat(),
            'total_selected': len(self.selected_nodes)
        })
        
        # Keep only last 100 selections
        if len(self.selection_history) > 100:
            self.selection_history = self.selection_history[-100:]
        
        self.logger.info(
            f"Node selected: {node_id} (mode: {selection_mode}, total: {len(self.selected_nodes)})",
            extra={
                'node_id': node_id,
                'selection_mode': selection_mode,
                'total_selected': len(self.selected_nodes),
                'event_id': event.event_id
            }
        )
        
        # Trigger UI updates
        self._update_selection_ui()
        self._update_context_menu()
    
    def _handle_node_deselected(self, event: Event) -> None:
        """Handle node deselection events."""
        ui_data = event.data.get('ui_data', {})
        node_id = ui_data.get('node_id')
        
        if node_id is None:
            # Deselect all
            self.selected_nodes.clear()
            self.logger.info("All nodes deselected")
        else:
            # Deselect specific node
            self.selected_nodes.discard(node_id)
            self.logger.info(f"Node deselected: {node_id}")
        
        # Record in history
        self.selection_history.append({
            'action': 'deselect',
            'node_id': node_id,
            'timestamp': event.timestamp.isoformat(),
            'total_selected': len(self.selected_nodes)
        })
        
        self._update_selection_ui()
        self._update_context_menu()
    
    def _handle_zoom_changed(self, event: Event) -> None:
        """Handle zoom change events."""
        ui_data = event.data.get('ui_data', {})
        new_zoom = ui_data.get('zoom_level')
        
        if new_zoom is not None:
            old_zoom = self.current_zoom_level
            self.current_zoom_level = new_zoom
            
            self.logger.debug(
                f"Zoom changed: {old_zoom:.2f} -> {new_zoom:.2f}",
                extra={
                    'old_zoom': old_zoom,
                    'new_zoom': new_zoom,
                    'event_id': event.event_id
                }
            )
            
            # Trigger zoom-dependent updates
            self._update_zoom_dependent_ui()
    
    def _handle_view_changed(self, event: Event) -> None:
        """Handle view change events."""
        ui_data = event.data.get('ui_data', {})
        
        if 'center_position' in ui_data:
            self.current_center_position = ui_data['center_position']
        
        if 'zoom_level' in ui_data:
            self.current_zoom_level = ui_data['zoom_level']
        
        self.logger.debug(
            f"View changed: center={self.current_center_position}, zoom={self.current_zoom_level}",
            extra={
                'center_position': self.current_center_position,
                'zoom_level': self.current_zoom_level,
                'event_id': event.event_id
            }
        )
        
        # Update viewport-dependent features
        self._update_viewport_dependent_ui()
    
    def _handle_filter_applied(self, event: Event) -> None:
        """Handle filter application events."""
        ui_data = event.data.get('ui_data', {})
        filter_type = ui_data.get('filter_type')
        filter_value = ui_data.get('filter_value')
        filter_active = ui_data.get('active', True)
        
        if filter_type:
            if filter_active:
                self.active_filters[filter_type] = filter_value
            else:
                self.active_filters.pop(filter_type, None)
            
            self.logger.info(
                f"Filter {'applied' if filter_active else 'removed'}: {filter_type} = {filter_value}",
                extra={
                    'filter_type': filter_type,
                    'filter_value': filter_value,
                    'active': filter_active,
                    'total_filters': len(self.active_filters),
                    'event_id': event.event_id
                }
            )
            
            # Trigger filter updates
            self._update_filtered_view()
    
    def _update_selection_ui(self) -> None:
        """Update UI elements based on current selection."""
        # This would integrate with the actual UI system
        self.logger.debug(f"Updating selection UI for {len(self.selected_nodes)} selected nodes")
    
    def _update_context_menu(self) -> None:
        """Update context menu based on current selection."""
        # This would integrate with the actual UI system
        self.logger.debug("Updating context menu")
    
    def _update_zoom_dependent_ui(self) -> None:
        """Update UI elements that depend on zoom level."""
        # This would integrate with the actual UI system
        self.logger.debug(f"Updating zoom-dependent UI for zoom level {self.current_zoom_level}")
    
    def _update_viewport_dependent_ui(self) -> None:
        """Update UI elements that depend on viewport."""
        # This would integrate with the actual UI system
        self.logger.debug("Updating viewport-dependent UI")
    
    def _update_filtered_view(self) -> None:
        """Update the view based on active filters."""
        # This would integrate with the actual UI system
        self.logger.debug(f"Updating filtered view with {len(self.active_filters)} active filters")
    
    def get_ui_stats(self) -> Dict[str, Any]:
        """Get UI-specific statistics."""
        return {
            'selected_nodes_count': len(self.selected_nodes),
            'selected_nodes': list(self.selected_nodes),
            'current_zoom_level': self.current_zoom_level,
            'current_center_position': self.current_center_position,
            'active_filters_count': len(self.active_filters),
            'active_filters': self.active_filters.copy(),
            'ui_interactions': self.ui_interaction_count,
            'selection_history_length': len(self.selection_history)
        }


class SystemEventHandler(BaseEventHandler):
    """Handler for system-related events."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("SystemEventHandler", logger)
        self.system_status = "running"
        self.error_count_by_component: Dict[str, int] = {}
        self.warning_count_by_component: Dict[str, int] = {}
        self.performance_issues: List[Dict[str, Any]] = []
        self.system_start_time: Optional[datetime] = None
        self.last_error_time: Optional[datetime] = None
    
    def get_handled_event_types(self) -> Set[EventType]:
        """Return system-related event types."""
        return {
            EventType.SYSTEM_STARTUP,
            EventType.SYSTEM_SHUTDOWN,
            EventType.SYSTEM_ERROR,
            EventType.SYSTEM_WARNING,
            EventType.PERFORMANCE_SLOW_OPERATION,
            EventType.PERFORMANCE_THRESHOLD_EXCEEDED,
            EventType.DATA_LOADED,
            EventType.DATA_SAVED,
            EventType.CACHE_HIT,
            EventType.CACHE_MISS,
            EventType.CACHE_INVALIDATED
        }
    
    def get_priority_for_event_type(self, event_type: EventType) -> int:
        """Get priority for system events."""
        priority_map = {
            EventType.SYSTEM_ERROR: 20,                    # Critical priority
            EventType.SYSTEM_SHUTDOWN: 15,                 # High priority
            EventType.SYSTEM_STARTUP: 15,                  # High priority
            EventType.PERFORMANCE_THRESHOLD_EXCEEDED: 12,  # High priority
            EventType.SYSTEM_WARNING: 8,                   # Medium-high priority
            EventType.PERFORMANCE_SLOW_OPERATION: 6,       # Medium priority
            EventType.DATA_SAVED: 5,                       # Normal priority
            EventType.DATA_LOADED: 5,                      # Normal priority
            EventType.CACHE_INVALIDATED: 4,                # Medium-low priority
            EventType.CACHE_MISS: 2,                       # Low priority
            EventType.CACHE_HIT: 1                         # Very low priority
        }
        return priority_map.get(event_type, 5)
    
    def handle_event(self, event: Event) -> None:
        """Handle system-related events."""
        if event.event_type == EventType.SYSTEM_STARTUP:
            self._handle_system_startup(event)
        elif event.event_type == EventType.SYSTEM_SHUTDOWN:
            self._handle_system_shutdown(event)
        elif event.event_type == EventType.SYSTEM_ERROR:
            self._handle_system_error(event)
        elif event.event_type == EventType.SYSTEM_WARNING:
            self._handle_system_warning(event)
        elif event.event_type == EventType.PERFORMANCE_SLOW_OPERATION:
            self._handle_slow_operation(event)
        elif event.event_type == EventType.PERFORMANCE_THRESHOLD_EXCEEDED:
            self._handle_performance_threshold_exceeded(event)
        elif event.event_type == EventType.DATA_LOADED:
            self._handle_data_loaded(event)
        elif event.event_type == EventType.DATA_SAVED:
            self._handle_data_saved(event)
        elif event.event_type in [EventType.CACHE_HIT, EventType.CACHE_MISS, EventType.CACHE_INVALIDATED]:
            self._handle_cache_event(event)
    
    def _handle_system_startup(self, event: Event) -> None:
        """Handle system startup events."""
        self.system_status = "starting"
        self.system_start_time = event.timestamp
        
        system_data = event.data.get('system_data', {})
        version = system_data.get('version', 'unknown')
        
        self.logger.info(
            f"System startup initiated - Version: {version}",
            extra={
                'version': version,
                'startup_time': event.timestamp.isoformat(),
                'event_id': event.event_id
            }
        )
        
        # Initialize system monitoring
        self._initialize_system_monitoring()
        
        # Mark system as running after startup
        self.system_status = "running"
    
    def _handle_system_shutdown(self, event: Event) -> None:
        """Handle system shutdown events."""
        self.system_status = "shutting_down"
        
        system_data = event.data.get('system_data', {})
        reason = system_data.get('reason', 'normal')
        
        uptime = None
        if self.system_start_time:
            uptime = (event.timestamp - self.system_start_time).total_seconds()
        
        self.logger.info(
            f"System shutdown initiated - Reason: {reason}, Uptime: {uptime}s",
            extra={
                'reason': reason,
                'uptime_seconds': uptime,
                'shutdown_time': event.timestamp.isoformat(),
                'event_id': event.event_id
            }
        )
        
        # Perform cleanup operations
        self._perform_shutdown_cleanup()
        
        self.system_status = "stopped"
    
    def _handle_system_error(self, event: Event) -> None:
        """Handle system error events."""
        system_component = event.data.get('system_component', 'unknown')
        error_message = event.data.get('message', 'Unknown error')
        system_data = event.data.get('system_data', {})
        error_code = system_data.get('error_code')
        
        # Track error counts
        self.error_count_by_component[system_component] = (
            self.error_count_by_component.get(system_component, 0) + 1
        )
        self.last_error_time = event.timestamp
        
        self.logger.error(
            f"System error in {system_component}: {error_message}",
            extra={
                'system_component': system_component,
                'error_code': error_code,
                'error_details': system_data.get('error_details', {}),
                'event_id': event.event_id
            }
        )
        
        # Check if error rate is too high
        self._check_error_rate_threshold(system_component)
        
        # Trigger error recovery if available
        self._attempt_error_recovery(system_component, error_code)
    
    def _handle_system_warning(self, event: Event) -> None:
        """Handle system warning events."""
        system_component = event.data.get('system_component', 'unknown')
        warning_message = event.data.get('message', 'Unknown warning')
        
        # Track warning counts
        self.warning_count_by_component[system_component] = (
            self.warning_count_by_component.get(system_component, 0) + 1
        )
        
        self.logger.warning(
            f"System warning in {system_component}: {warning_message}",
            extra={
                'system_component': system_component,
                'event_id': event.event_id
            }
        )
    
    def _handle_slow_operation(self, event: Event) -> None:
        """Handle slow operation events."""
        operation_name = event.data.get('operation_name', 'unknown')
        duration_ms = event.data.get('duration_ms', 0)
        threshold_ms = event.data.get('threshold_ms', 1000)
        performance_data = event.data.get('performance_data', {})
        component = performance_data.get('component', 'unknown')
        
        # Record performance issue
        performance_issue = {
            'operation_name': operation_name,
            'component': component,
            'duration_ms': duration_ms,
            'threshold_ms': threshold_ms,
            'timestamp': event.timestamp.isoformat(),
            'event_id': event.event_id
        }
        
        self.performance_issues.append(performance_issue)
        
        # Keep only last 100 performance issues
        if len(self.performance_issues) > 100:
            self.performance_issues = self.performance_issues[-100:]
        
        self.logger.warning(
            f"Slow operation detected: {operation_name} in {component} took {duration_ms}ms (threshold: {threshold_ms}ms)",
            extra=performance_issue
        )
        
        # Check if component has too many slow operations
        self._check_performance_degradation(component)
    
    def _handle_performance_threshold_exceeded(self, event: Event) -> None:
        """Handle performance threshold exceeded events."""
        self.logger.error(
            "Performance threshold exceeded",
            extra={
                'event_data': event.data,
                'event_id': event.event_id
            }
        )
        
        # This could trigger alerts or automatic scaling
        self._handle_performance_crisis()
    
    def _handle_data_loaded(self, event: Event) -> None:
        """Handle data loaded events."""
        data_source = event.data.get('data_source', 'unknown')
        data_info = event.data.get('data_info', {})
        record_count = data_info.get('record_count', 0)
        load_duration_ms = data_info.get('load_duration_ms')
        
        self.logger.info(
            f"Data loaded from {data_source}: {record_count} records" +
            (f" in {load_duration_ms}ms" if load_duration_ms else ""),
            extra={
                'data_source': data_source,
                'record_count': record_count,
                'load_duration_ms': load_duration_ms,
                'event_id': event.event_id
            }
        )
    
    def _handle_data_saved(self, event: Event) -> None:
        """Handle data saved events."""
        data_source = event.data.get('data_source', 'unknown')
        data_info = event.data.get('data_info', {})
        record_count = data_info.get('record_count', 0)
        save_duration_ms = data_info.get('save_duration_ms')
        backup_created = data_info.get('backup_created', False)
        
        self.logger.info(
            f"Data saved to {data_source}: {record_count} records" +
            (f" in {save_duration_ms}ms" if save_duration_ms else "") +
            (" (backup created)" if backup_created else ""),
            extra={
                'data_source': data_source,
                'record_count': record_count,
                'save_duration_ms': save_duration_ms,
                'backup_created': backup_created,
                'event_id': event.event_id
            }
        )
    
    def _handle_cache_event(self, event: Event) -> None:
        """Handle cache-related events."""
        cache_name = event.data.get('cache_name', 'unknown')
        cache_key = event.data.get('cache_key')
        
        if event.event_type == EventType.CACHE_HIT:
            self.logger.debug(f"Cache hit: {cache_name}[{cache_key}]")
        elif event.event_type == EventType.CACHE_MISS:
            self.logger.debug(f"Cache miss: {cache_name}[{cache_key}]")
        elif event.event_type == EventType.CACHE_INVALIDATED:
            self.logger.info(f"Cache invalidated: {cache_name}[{cache_key}]")
    
    def _initialize_system_monitoring(self) -> None:
        """Initialize system monitoring."""
        self.logger.info("Initializing system monitoring")
    
    def _perform_shutdown_cleanup(self) -> None:
        """Perform cleanup operations during shutdown."""
        self.logger.info("Performing shutdown cleanup")
    
    def _check_error_rate_threshold(self, component: str) -> None:
        """Check if error rate for a component is too high."""
        error_count = self.error_count_by_component.get(component, 0)
        if error_count > 10:  # Threshold
            self.logger.critical(f"High error rate detected in {component}: {error_count} errors")
    
    def _attempt_error_recovery(self, component: str, error_code: Optional[str]) -> None:
        """Attempt to recover from errors."""
        self.logger.info(f"Attempting error recovery for {component} (error: {error_code})")
    
    def _check_performance_degradation(self, component: str) -> None:
        """Check if a component has performance degradation."""
        recent_issues = [
            issue for issue in self.performance_issues[-20:]  # Last 20 issues
            if issue['component'] == component
        ]
        
        if len(recent_issues) > 5:  # Threshold
            self.logger.warning(f"Performance degradation detected in {component}: {len(recent_issues)} slow operations")
    
    def _handle_performance_crisis(self) -> None:
        """Handle performance crisis situations."""
        self.logger.critical("Performance crisis detected - taking emergency measures")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-specific statistics."""
        uptime = None
        if self.system_start_time:
            uptime = (datetime.now() - self.system_start_time).total_seconds()
        
        return {
            'system_status': self.system_status,
            'uptime_seconds': uptime,
            'total_errors': sum(self.error_count_by_component.values()),
            'total_warnings': sum(self.warning_count_by_component.values()),
            'errors_by_component': self.error_count_by_component.copy(),
            'warnings_by_component': self.warning_count_by_component.copy(),
            'performance_issues_count': len(self.performance_issues),
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'system_start_time': self.system_start_time.isoformat() if self.system_start_time else None
        }


class EventHandlerRegistry:
    """Registry for managing event handlers."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        self.handlers: Dict[str, BaseEventHandler] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_handler(self, handler: BaseEventHandler) -> None:
        """Register an event handler."""
        if handler.name in self.handlers:
            self.logger.warning(f"Handler {handler.name} already registered, replacing")
            self.unregister_handler(handler.name)
        
        self.handlers[handler.name] = handler
        handler.register(self.event_bus)
        
        self.logger.info(f"Registered event handler: {handler.name}")
    
    def unregister_handler(self, handler_name: str) -> bool:
        """Unregister an event handler."""
        if handler_name not in self.handlers:
            return False
        
        handler = self.handlers[handler_name]
        handler.unregister(self.event_bus)
        del self.handlers[handler_name]
        
        self.logger.info(f"Unregistered event handler: {handler_name}")
        return True
    
    def get_handler(self, handler_name: str) -> Optional[BaseEventHandler]:
        """Get a registered handler by name."""
        return self.handlers.get(handler_name)
    
    def get_all_handlers(self) -> Dict[str, BaseEventHandler]:
        """Get all registered handlers."""
        return self.handlers.copy()
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        handler_stats = {}
        for name, handler in self.handlers.items():
            handler_stats[name] = handler.get_stats()
        
        return {
            'total_handlers': len(self.handlers),
            'handler_names': list(self.handlers.keys()),
            'handler_stats': handler_stats
        }
    
    def shutdown_all_handlers(self) -> None:
        """Shutdown all registered handlers."""
        for handler_name in list(self.handlers.keys()):
            self.unregister_handler(handler_name)
        
        self.logger.info("All event handlers shut down")


# Global handler registry
_handler_registry: Optional[EventHandlerRegistry] = None


def get_handler_registry() -> EventHandlerRegistry:
    """Get the global handler registry."""
    global _handler_registry
    if _handler_registry is None:
        _handler_registry = EventHandlerRegistry()
    return _handler_registry


def setup_default_handlers() -> None:
    """Set up default event handlers."""
    registry = get_handler_registry()
    
    # Register default handlers
    registry.register_handler(NodeEventHandler())
    registry.register_handler(UIEventHandler())
    registry.register_handler(SystemEventHandler())
    
    logging.getLogger(__name__).info("Default event handlers registered")


def setup_default_event_handlers() -> None:
    """Set up default event handlers (alias for setup_default_handlers)."""
    setup_default_handlers()


def get_ui_event_handler() -> Optional[UIEventHandler]:
    """Get the UI event handler from the registry."""
    registry = get_handler_registry()
    for handler in registry.handlers.values():
        if isinstance(handler, UIEventHandler):
            return handler
    return None


def get_cache_event_handler() -> Optional[SystemEventHandler]:
    """Get the cache/system event handler from the registry."""
    registry = get_handler_registry()
    for handler in registry.handlers.values():
        if isinstance(handler, SystemEventHandler):
            return handler
    return None


def shutdown_handlers() -> None:
    """Shutdown all event handlers."""
    registry = get_handler_registry()
    registry.shutdown_all_handlers()
    
    logging.getLogger(__name__).info("Event handlers shut down")