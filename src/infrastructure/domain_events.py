"""
Domain-specific event classes for the Enhanced Mind Map application.

This module provides specialized event classes for different domains
with proper typing and validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime

from src.infrastructure.event_system import Event, EventType, EventMetadata, EventPriority


@dataclass
class NodeEvent(Event):
    """Base class for node-related events."""
    
    def __init__(
        self,
        event_type: EventType,
        node_id: int,
        node_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        data = {
            'node_id': node_id,
            'node_data': node_data or {}
        }
        data.update(kwargs.get('data', {}))
        
        super().__init__(
            event_type=event_type,
            data=data,
            **{k: v for k, v in kwargs.items() if k != 'data'}
        )
    
    @property
    def node_id(self) -> int:
        """Get the node ID from event data."""
        return self.data['node_id']
    
    @property
    def node_data(self) -> Dict[str, Any]:
        """Get the node data from event data."""
        return self.data.get('node_data', {})


@dataclass
class NodeCreatedEvent(NodeEvent):
    """Event fired when a new node is created."""
    
    def __init__(
        self,
        node_id: int,
        title: str,
        content: str = "",
        parent_id: Optional[int] = None,
        position: Optional[Dict[str, float]] = None,
        **kwargs
    ):
        node_data = {
            'title': title,
            'content': content,
            'parent_id': parent_id,
            'position': position or {'x': 0, 'y': 0}
        }
        
        super().__init__(
            event_type=EventType.NODE_CREATED,
            node_id=node_id,
            node_data=node_data,
            priority=EventPriority.HIGH,
            **kwargs
        )
    
    @property
    def title(self) -> str:
        return self.node_data['title']
    
    @property
    def content(self) -> str:
        return self.node_data['content']
    
    @property
    def parent_id(self) -> Optional[int]:
        return self.node_data.get('parent_id')
    
    @property
    def position(self) -> Dict[str, float]:
        return self.node_data['position']


@dataclass
class NodeUpdatedEvent(NodeEvent):
    """Event fired when a node is updated."""
    
    def __init__(
        self,
        node_id: int,
        changes: Dict[str, Any],
        old_values: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        node_data = {
            'changes': changes,
            'old_values': old_values or {}
        }
        
        super().__init__(
            event_type=EventType.NODE_UPDATED,
            node_id=node_id,
            node_data=node_data,
            priority=EventPriority.NORMAL,
            **kwargs
        )
    
    @property
    def changes(self) -> Dict[str, Any]:
        return self.node_data['changes']
    
    @property
    def old_values(self) -> Dict[str, Any]:
        return self.node_data.get('old_values', {})


@dataclass
class NodeDeletedEvent(NodeEvent):
    """Event fired when a node is deleted."""
    
    def __init__(
        self,
        node_id: int,
        deleted_node_data: Dict[str, Any],
        cascade_deleted: Optional[List[int]] = None,
        **kwargs
    ):
        node_data = {
            'deleted_node_data': deleted_node_data,
            'cascade_deleted': cascade_deleted or []
        }
        
        super().__init__(
            event_type=EventType.NODE_DELETED,
            node_id=node_id,
            node_data=node_data,
            priority=EventPriority.HIGH,
            **kwargs
        )
    
    @property
    def deleted_node_data(self) -> Dict[str, Any]:
        return self.node_data['deleted_node_data']
    
    @property
    def cascade_deleted(self) -> List[int]:
        return self.node_data.get('cascade_deleted', [])


@dataclass
class NodeMovedEvent(NodeEvent):
    """Event fired when a node is moved."""
    
    def __init__(
        self,
        node_id: int,
        old_position: Dict[str, float],
        new_position: Dict[str, float],
        **kwargs
    ):
        node_data = {
            'old_position': old_position,
            'new_position': new_position
        }
        
        super().__init__(
            event_type=EventType.NODE_MOVED,
            node_id=node_id,
            node_data=node_data,
            priority=EventPriority.LOW,
            **kwargs
        )
    
    @property
    def old_position(self) -> Dict[str, float]:
        return self.node_data['old_position']
    
    @property
    def new_position(self) -> Dict[str, float]:
        return self.node_data['new_position']


@dataclass
class UIEvent(Event):
    """Base class for UI-related events."""
    
    def __init__(
        self,
        event_type: EventType,
        component: str,
        action: str,
        ui_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        data = {
            'component': component,
            'action': action,
            'ui_data': ui_data or {}
        }
        data.update(kwargs.get('data', {}))
        
        super().__init__(
            event_type=event_type,
            data=data,
            **{k: v for k, v in kwargs.items() if k != 'data'}
        )
    
    @property
    def component(self) -> str:
        return self.data['component']
    
    @property
    def action(self) -> str:
        return self.data['action']
    
    @property
    def ui_data(self) -> Dict[str, Any]:
        return self.data.get('ui_data', {})


@dataclass
class NodeSelectionEvent(UIEvent):
    """Event fired when a node is selected/deselected in the UI."""
    
    def __init__(
        self,
        node_id: Optional[int],
        selected: bool,
        selection_mode: str = "single",
        **kwargs
    ):
        event_type = EventType.UI_NODE_SELECTED if selected else EventType.UI_NODE_DESELECTED
        ui_data = {
            'node_id': node_id,
            'selected': selected,
            'selection_mode': selection_mode
        }
        
        super().__init__(
            event_type=event_type,
            component="node_selector",
            action="selection_changed",
            ui_data=ui_data,
            priority=EventPriority.LOW,
            **kwargs
        )
    
    @property
    def node_id(self) -> Optional[int]:
        return self.ui_data.get('node_id')
    
    @property
    def selected(self) -> bool:
        return self.ui_data['selected']
    
    @property
    def selection_mode(self) -> str:
        return self.ui_data['selection_mode']


@dataclass
class ViewChangeEvent(UIEvent):
    """Event fired when the view changes (zoom, pan, etc.)."""
    
    def __init__(
        self,
        zoom_level: Optional[float] = None,
        center_position: Optional[Dict[str, float]] = None,
        viewport_size: Optional[Dict[str, float]] = None,
        **kwargs
    ):
        ui_data = {}
        if zoom_level is not None:
            ui_data['zoom_level'] = zoom_level
        if center_position is not None:
            ui_data['center_position'] = center_position
        if viewport_size is not None:
            ui_data['viewport_size'] = viewport_size
        
        super().__init__(
            event_type=EventType.UI_VIEW_CHANGED,
            component="viewport",
            action="view_changed",
            ui_data=ui_data,
            priority=EventPriority.LOW,
            **kwargs
        )
    
    @property
    def zoom_level(self) -> Optional[float]:
        return self.ui_data.get('zoom_level')
    
    @property
    def center_position(self) -> Optional[Dict[str, float]]:
        return self.ui_data.get('center_position')
    
    @property
    def viewport_size(self) -> Optional[Dict[str, float]]:
        return self.ui_data.get('viewport_size')


@dataclass
class SystemEvent(Event):
    """Base class for system-related events."""
    
    def __init__(
        self,
        event_type: EventType,
        system_component: str,
        message: str,
        system_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        data = {
            'system_component': system_component,
            'message': message,
            'system_data': system_data or {}
        }
        data.update(kwargs.get('data', {}))
        
        super().__init__(
            event_type=event_type,
            data=data,
            **{k: v for k, v in kwargs.items() if k != 'data'}
        )
    
    @property
    def system_component(self) -> str:
        return self.data['system_component']
    
    @property
    def message(self) -> str:
        return self.data['message']
    
    @property
    def system_data(self) -> Dict[str, Any]:
        return self.data.get('system_data', {})


@dataclass
class SystemErrorEvent(SystemEvent):
    """Event fired when a system error occurs."""
    
    def __init__(
        self,
        system_component: str,
        error_message: str,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        system_data = {
            'error_code': error_code,
            'error_details': error_details or {}
        }
        
        super().__init__(
            event_type=EventType.SYSTEM_ERROR,
            system_component=system_component,
            message=error_message,
            system_data=system_data,
            priority=EventPriority.CRITICAL,
            **kwargs
        )
    
    @property
    def error_code(self) -> Optional[str]:
        return self.system_data.get('error_code')
    
    @property
    def error_details(self) -> Dict[str, Any]:
        return self.system_data.get('error_details', {})


@dataclass
class DataEvent(Event):
    """Base class for data-related events."""
    
    def __init__(
        self,
        event_type: EventType,
        operation: str,
        data_source: str,
        data_info: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        data = {
            'operation': operation,
            'data_source': data_source,
            'data_info': data_info or {}
        }
        data.update(kwargs.get('data', {}))
        
        super().__init__(
            event_type=event_type,
            data=data,
            **{k: v for k, v in kwargs.items() if k != 'data'}
        )
    
    @property
    def operation(self) -> str:
        return self.data['operation']
    
    @property
    def data_source(self) -> str:
        return self.data['data_source']
    
    @property
    def data_info(self) -> Dict[str, Any]:
        return self.data.get('data_info', {})


@dataclass
class DataLoadedEvent(DataEvent):
    """Event fired when data is loaded."""
    
    def __init__(
        self,
        data_source: str,
        record_count: int,
        load_duration_ms: Optional[float] = None,
        **kwargs
    ):
        data_info = {
            'record_count': record_count,
            'load_duration_ms': load_duration_ms
        }
        
        super().__init__(
            event_type=EventType.DATA_LOADED,
            operation="load",
            data_source=data_source,
            data_info=data_info,
            priority=EventPriority.NORMAL,
            **kwargs
        )
    
    @property
    def record_count(self) -> int:
        return self.data_info['record_count']
    
    @property
    def load_duration_ms(self) -> Optional[float]:
        return self.data_info.get('load_duration_ms')


@dataclass
class DataSavedEvent(DataEvent):
    """Event fired when data is saved."""
    
    def __init__(
        self,
        data_source: str,
        record_count: int,
        save_duration_ms: Optional[float] = None,
        backup_created: bool = False,
        **kwargs
    ):
        data_info = {
            'record_count': record_count,
            'save_duration_ms': save_duration_ms,
            'backup_created': backup_created
        }
        
        super().__init__(
            event_type=EventType.DATA_SAVED,
            operation="save",
            data_source=data_source,
            data_info=data_info,
            priority=EventPriority.NORMAL,
            **kwargs
        )
    
    @property
    def record_count(self) -> int:
        return self.data_info['record_count']
    
    @property
    def save_duration_ms(self) -> Optional[float]:
        return self.data_info.get('save_duration_ms')
    
    @property
    def backup_created(self) -> bool:
        return self.data_info.get('backup_created', False)


@dataclass
class PerformanceEvent(Event):
    """Base class for performance-related events."""
    
    def __init__(
        self,
        event_type: EventType,
        operation_name: str,
        duration_ms: float,
        threshold_ms: Optional[float] = None,
        performance_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        data = {
            'operation_name': operation_name,
            'duration_ms': duration_ms,
            'threshold_ms': threshold_ms,
            'performance_data': performance_data or {}
        }
        data.update(kwargs.get('data', {}))
        
        super().__init__(
            event_type=event_type,
            data=data,
            **{k: v for k, v in kwargs.items() if k != 'data'}
        )
    
    @property
    def operation_name(self) -> str:
        return self.data['operation_name']
    
    @property
    def duration_ms(self) -> float:
        return self.data['duration_ms']
    
    @property
    def threshold_ms(self) -> Optional[float]:
        return self.data.get('threshold_ms')
    
    @property
    def performance_data(self) -> Dict[str, Any]:
        return self.data.get('performance_data', {})


@dataclass
class SlowOperationEvent(PerformanceEvent):
    """Event fired when an operation exceeds performance thresholds."""
    
    def __init__(
        self,
        operation_name: str,
        duration_ms: float,
        threshold_ms: float,
        component: str,
        **kwargs
    ):
        performance_data = {
            'component': component,
            'threshold_exceeded_by_ms': duration_ms - threshold_ms,
            'threshold_exceeded_by_percent': ((duration_ms - threshold_ms) / threshold_ms) * 100
        }
        
        super().__init__(
            event_type=EventType.PERFORMANCE_SLOW_OPERATION,
            operation_name=operation_name,
            duration_ms=duration_ms,
            threshold_ms=threshold_ms,
            performance_data=performance_data,
            priority=EventPriority.HIGH,
            **kwargs
        )
    
    @property
    def component(self) -> str:
        return self.performance_data['component']
    
    @property
    def threshold_exceeded_by_ms(self) -> float:
        return self.performance_data['threshold_exceeded_by_ms']
    
    @property
    def threshold_exceeded_by_percent(self) -> float:
        return self.performance_data['threshold_exceeded_by_percent']


# Event factory functions for easy creation
def create_node_created_event(node_id: int, title: str, **kwargs) -> NodeCreatedEvent:
    """Create a node created event."""
    return NodeCreatedEvent(node_id=node_id, title=title, **kwargs)


def create_node_updated_event(node_id: int, changes: Dict[str, Any], **kwargs) -> NodeUpdatedEvent:
    """Create a node updated event."""
    return NodeUpdatedEvent(node_id=node_id, changes=changes, **kwargs)


def create_node_deleted_event(node_id: int, deleted_node_data: Dict[str, Any], **kwargs) -> NodeDeletedEvent:
    """Create a node deleted event."""
    return NodeDeletedEvent(node_id=node_id, deleted_node_data=deleted_node_data, **kwargs)


def create_system_error_event(component: str, error_message: str, **kwargs) -> SystemErrorEvent:
    """Create a system error event."""
    return SystemErrorEvent(system_component=component, error_message=error_message, **kwargs)


def create_data_loaded_event(data_source: str, record_count: int, **kwargs) -> DataLoadedEvent:
    """Create a data loaded event."""
    return DataLoadedEvent(data_source=data_source, record_count=record_count, **kwargs)


def create_slow_operation_event(operation_name: str, duration_ms: float, threshold_ms: float, component: str, **kwargs) -> SlowOperationEvent:
    """Create a slow operation event."""
    return SlowOperationEvent(
        operation_name=operation_name,
        duration_ms=duration_ms,
        threshold_ms=threshold_ms,
        component=component,
        **kwargs
    )