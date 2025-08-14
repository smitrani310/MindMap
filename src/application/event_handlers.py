"""
Event handlers for the Enhanced Mind Map application.

This module contains specific event handlers for different types of events
in the mind map system.
"""

import logging
from typing import Dict, Any, Optional

from src.infrastructure.events import Event, EventHandler, EventType, get_event_bus
from src.infrastructure.cache import get_cache_manager, invalidate_node_cache, invalidate_search_cache
from src.infrastructure.performance import get_performance_monitor


class NodeEventHandler(EventHandler):
    """Handles node-related events."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.NodeEventHandler")
        self.cache_manager = get_cache_manager()
    
    @property
    def name(self) -> str:
        return "NodeEventHandler"
    
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process node events."""
        return event.type in [
            EventType.NODE_CREATED,
            EventType.NODE_UPDATED,
            EventType.NODE_DELETED,
            EventType.NODE_MOVED
        ]
    
    def handle(self, event: Event) -> None:
        """Handle node events."""
        node_id = event.data.get('node_id')
        if node_id is None:
            self.logger.warning(f"Node event {event.type.value} missing node_id")
            return
        
        self.logger.info(f"Handling {event.type.value} for node {node_id}")
        
        if event.type == EventType.NODE_CREATED:
            self._handle_node_created(event)
        elif event.type == EventType.NODE_UPDATED:
            self._handle_node_updated(event)
        elif event.type == EventType.NODE_DELETED:
            self._handle_node_deleted(event)
        elif event.type == EventType.NODE_MOVED:
            self._handle_node_moved(event)
    
    def _handle_node_created(self, event: Event) -> None:
        """Handle node creation event."""
        node_id = event.data['node_id']
        
        # Invalidate relevant caches
        invalidate_search_cache()
        
        # Log the creation
        self.logger.info(f"Node {node_id} created by {event.source}")
        
        # Publish a cache invalidation event
        get_event_bus().publish(Event(
            type=EventType.CACHE_INVALIDATED,
            source="NodeEventHandler",
            data={'cache_type': 'search', 'reason': 'node_created', 'node_id': node_id}
        ))
    
    def _handle_node_updated(self, event: Event) -> None:
        """Handle node update event."""
        node_id = event.data['node_id']
        
        # Invalidate node-specific caches
        invalidate_node_cache(node_id)
        invalidate_search_cache()
        
        # Log the update
        updated_fields = event.data.get('updated_fields', [])
        self.logger.info(f"Node {node_id} updated by {event.source}, fields: {updated_fields}")
        
        # Publish cache invalidation events
        get_event_bus().publish(Event(
            type=EventType.CACHE_INVALIDATED,
            source="NodeEventHandler",
            data={'cache_type': 'node', 'reason': 'node_updated', 'node_id': node_id}
        ))
    
    def _handle_node_deleted(self, event: Event) -> None:
        """Handle node deletion event."""
        node_id = event.data['node_id']
        deleted_count = event.data.get('deleted_count', 1)
        
        # Invalidate all relevant caches
        invalidate_node_cache(node_id)
        invalidate_search_cache()
        
        # Log the deletion
        self.logger.info(f"Node {node_id} and {deleted_count} descendants deleted by {event.source}")
        
        # Publish cache invalidation event
        get_event_bus().publish(Event(
            type=EventType.CACHE_INVALIDATED,
            source="NodeEventHandler",
            data={'cache_type': 'all', 'reason': 'node_deleted', 'node_id': node_id}
        ))
    
    def _handle_node_moved(self, event: Event) -> None:
        """Handle node move event."""
        node_id = event.data['node_id']
        old_position = event.data.get('old_position')
        new_position = event.data.get('new_position')
        
        # Invalidate render caches since position changed
        if self.cache_manager:
            self.cache_manager.invalidate_cache('render')
        
        self.logger.info(f"Node {node_id} moved from {old_position} to {new_position}")


class UIEventHandler(EventHandler):
    """Handles UI-related events."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.UIEventHandler")
        self.selected_nodes: set = set()
    
    @property
    def name(self) -> str:
        return "UIEventHandler"
    
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process UI events."""
        return event.type in [
            EventType.UI_NODE_SELECTED,
            EventType.UI_NODE_DESELECTED,
            EventType.UI_ZOOM_CHANGED,
            EventType.UI_PAN_CHANGED
        ]
    
    def handle(self, event: Event) -> None:
        """Handle UI events."""
        self.logger.debug(f"Handling UI event {event.type.value}")
        
        if event.type == EventType.UI_NODE_SELECTED:
            self._handle_node_selected(event)
        elif event.type == EventType.UI_NODE_DESELECTED:
            self._handle_node_deselected(event)
        elif event.type == EventType.UI_ZOOM_CHANGED:
            self._handle_zoom_changed(event)
        elif event.type == EventType.UI_PAN_CHANGED:
            self._handle_pan_changed(event)
    
    def _handle_node_selected(self, event: Event) -> None:
        """Handle node selection event."""
        node_id = event.data.get('node_id')
        if node_id:
            self.selected_nodes.add(node_id)
            self.logger.debug(f"Node {node_id} selected, total selected: {len(self.selected_nodes)}")
    
    def _handle_node_deselected(self, event: Event) -> None:
        """Handle node deselection event."""
        node_id = event.data.get('node_id')
        if node_id and node_id in self.selected_nodes:
            self.selected_nodes.remove(node_id)
            self.logger.debug(f"Node {node_id} deselected, total selected: {len(self.selected_nodes)}")
    
    def _handle_zoom_changed(self, event: Event) -> None:
        """Handle zoom change event."""
        zoom_level = event.data.get('zoom_level')
        self.logger.debug(f"Zoom changed to {zoom_level}")
        
        # Invalidate render cache since zoom affects rendering
        cache_manager = get_cache_manager()
        if cache_manager:
            cache_manager.invalidate_cache('render')
    
    def _handle_pan_changed(self, event: Event) -> None:
        """Handle pan change event."""
        pan_x = event.data.get('pan_x')
        pan_y = event.data.get('pan_y')
        self.logger.debug(f"Pan changed to ({pan_x}, {pan_y})")
        
        # Invalidate render cache since pan affects rendering
        cache_manager = get_cache_manager()
        if cache_manager:
            cache_manager.invalidate_cache('render')
    
    def get_selected_nodes(self) -> set:
        """Get currently selected nodes."""
        return self.selected_nodes.copy()


class SystemEventHandler(EventHandler):
    """Handles system-level events."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SystemEventHandler")
        self.performance_monitor = get_performance_monitor()
    
    @property
    def name(self) -> str:
        return "SystemEventHandler"
    
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process system events."""
        return event.type in [
            EventType.SYSTEM_ERROR,
            EventType.SYSTEM_WARNING,
            EventType.SYSTEM_INFO,
            EventType.MINDMAP_LOADED,
            EventType.MINDMAP_SAVED,
            EventType.MINDMAP_CLEARED
        ]
    
    def handle(self, event: Event) -> None:
        """Handle system events."""
        if event.type == EventType.SYSTEM_ERROR:
            self._handle_system_error(event)
        elif event.type == EventType.SYSTEM_WARNING:
            self._handle_system_warning(event)
        elif event.type == EventType.SYSTEM_INFO:
            self._handle_system_info(event)
        elif event.type == EventType.MINDMAP_LOADED:
            self._handle_mindmap_loaded(event)
        elif event.type == EventType.MINDMAP_SAVED:
            self._handle_mindmap_saved(event)
        elif event.type == EventType.MINDMAP_CLEARED:
            self._handle_mindmap_cleared(event)
    
    def _handle_system_error(self, event: Event) -> None:
        """Handle system error event."""
        error_message = event.data.get('message', 'Unknown error')
        error_type = event.data.get('error_type', 'SystemError')
        
        self.logger.error(f"System error from {event.source}: {error_type} - {error_message}")
        
        # Record error in performance monitor if available
        if self.performance_monitor:
            self.performance_monitor.record_metric(
                operation=f"system_error.{error_type}",
                duration_ms=0,
                success=False,
                error=error_message
            )
    
    def _handle_system_warning(self, event: Event) -> None:
        """Handle system warning event."""
        warning_message = event.data.get('message', 'Unknown warning')
        self.logger.warning(f"System warning from {event.source}: {warning_message}")
    
    def _handle_system_info(self, event: Event) -> None:
        """Handle system info event."""
        info_message = event.data.get('message', 'System info')
        self.logger.info(f"System info from {event.source}: {info_message}")
    
    def _handle_mindmap_loaded(self, event: Event) -> None:
        """Handle mind map loaded event."""
        node_count = event.data.get('node_count', 0)
        file_path = event.data.get('file_path', 'unknown')
        
        self.logger.info(f"Mind map loaded from {file_path} with {node_count} nodes")
        
        # Clear all caches when new data is loaded
        cache_manager = get_cache_manager()
        if cache_manager:
            for cache_name in ['nodes', 'render', 'computation', 'search']:
                cache_manager.invalidate_cache(cache_name)
    
    def _handle_mindmap_saved(self, event: Event) -> None:
        """Handle mind map saved event."""
        file_path = event.data.get('file_path', 'unknown')
        node_count = event.data.get('node_count', 0)
        
        self.logger.info(f"Mind map saved to {file_path} with {node_count} nodes")
    
    def _handle_mindmap_cleared(self, event: Event) -> None:
        """Handle mind map cleared event."""
        self.logger.info("Mind map cleared")
        
        # Clear all caches when data is cleared
        cache_manager = get_cache_manager()
        if cache_manager:
            for cache_name in ['nodes', 'render', 'computation', 'search']:
                cache_manager.invalidate_cache(cache_name)


class CacheEventHandler(EventHandler):
    """Handles cache-related events."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.CacheEventHandler")
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
    
    @property
    def name(self) -> str:
        return "CacheEventHandler"
    
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process cache events."""
        return event.type in [
            EventType.CACHE_HIT,
            EventType.CACHE_MISS,
            EventType.CACHE_INVALIDATED
        ]
    
    def handle(self, event: Event) -> None:
        """Handle cache events."""
        if event.type == EventType.CACHE_HIT:
            self._handle_cache_hit(event)
        elif event.type == EventType.CACHE_MISS:
            self._handle_cache_miss(event)
        elif event.type == EventType.CACHE_INVALIDATED:
            self._handle_cache_invalidated(event)
    
    def _handle_cache_hit(self, event: Event) -> None:
        """Handle cache hit event."""
        cache_type = event.data.get('cache_type', 'unknown')
        cache_key = event.data.get('cache_key', 'unknown')
        
        self.cache_stats['hits'] += 1
        self.logger.debug(f"Cache hit: {cache_type}:{cache_key}")
    
    def _handle_cache_miss(self, event: Event) -> None:
        """Handle cache miss event."""
        cache_type = event.data.get('cache_type', 'unknown')
        cache_key = event.data.get('cache_key', 'unknown')
        
        self.cache_stats['misses'] += 1
        self.logger.debug(f"Cache miss: {cache_type}:{cache_key}")
    
    def _handle_cache_invalidated(self, event: Event) -> None:
        """Handle cache invalidation event."""
        cache_type = event.data.get('cache_type', 'unknown')
        reason = event.data.get('reason', 'unknown')
        
        self.cache_stats['invalidations'] += 1
        self.logger.debug(f"Cache invalidated: {cache_type} (reason: {reason})")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache event statistics."""
        return self.cache_stats.copy()


def setup_default_event_handlers() -> None:
    """Set up the default event handlers for the application."""
    event_bus = get_event_bus()
    
    # Add all default handlers
    event_bus.add_handler(NodeEventHandler())
    event_bus.add_handler(UIEventHandler())
    event_bus.add_handler(SystemEventHandler())
    event_bus.add_handler(CacheEventHandler())
    
    logger = logging.getLogger(__name__)
    logger.info("Default event handlers set up successfully")


def get_ui_event_handler() -> Optional[UIEventHandler]:
    """Get the UI event handler instance."""
    event_bus = get_event_bus()
    
    for handler in event_bus.handlers:
        if isinstance(handler, UIEventHandler):
            return handler
    
    return None


def get_cache_event_handler() -> Optional[CacheEventHandler]:
    """Get the cache event handler instance."""
    event_bus = get_event_bus()
    
    for handler in event_bus.handlers:
        if isinstance(handler, CacheEventHandler):
            return handler
    
    return None