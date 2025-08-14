# Design Document

## Overview

This design document outlines the architectural improvements for the Enhanced Mind Map application. The design focuses on creating a more maintainable, performant, and scalable codebase while preserving all existing functionality and ensuring backward compatibility.

## Architecture

### Current Architecture Analysis

The current application follows a monolithic Streamlit architecture with the following characteristics:
- Single main.py entry point (~400 lines)
- Direct JSON file storage
- URL parameter-based frontend-backend communication
- Modular UI components but tightly coupled business logic
- Manual state management throughout the application

### Target Architecture

The improved architecture will implement a layered approach with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   UI Components │  │   Event Handlers│  │   Validators│ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │    Services     │  │   Use Cases     │  │   Commands  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │    Entities     │  │  Value Objects  │  │   Policies  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Repositories   │  │   Config Mgmt   │  │   Logging   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Data Layer Abstraction

#### Repository Pattern Implementation

```python
# Abstract base repository
class MindMapRepository(ABC):
    @abstractmethod
    def save(self, mindmap: MindMapData) -> Result[bool, Error]
    
    @abstractmethod
    def load(self) -> Result[MindMapData, Error]
    
    @abstractmethod
    def backup(self) -> Result[str, Error]
    
    @abstractmethod
    def restore(self, backup_path: str) -> Result[bool, Error]

# JSON file implementation
class JsonMindMapRepository(MindMapRepository):
    def __init__(self, file_path: str, backup_dir: str):
        self.file_path = file_path
        self.backup_dir = backup_dir
    
    def save(self, mindmap: MindMapData) -> Result[bool, Error]:
        # Implementation with validation and atomic writes
        pass

# Future: Database implementation
class DatabaseMindMapRepository(MindMapRepository):
    # Implementation for database storage
    pass
```

#### Data Models

```python
@dataclass
class Node:
    id: int
    label: str
    description: str
    position: Position
    urgency: UrgencyLevel
    tag: str
    parent_id: Optional[int]
    edge_type: EdgeType
    created_at: datetime
    updated_at: datetime

@dataclass
class MindMapData:
    nodes: List[Node]
    central_node_id: Optional[int]
    settings: MindMapSettings
    metadata: MindMapMetadata
```

### 2. Configuration Management

#### Centralized Configuration System

```python
class AppConfig(BaseSettings):
    # File paths
    data_file: str = "mindmap_data.json"
    backup_dir: str = "backups"
    log_dir: str = "logs"
    
    # Application settings
    theme: str = "default"
    canvas_width: int = 800
    canvas_height: int = 600
    auto_save_interval: int = 30  # seconds
    
    # Performance settings
    cache_size: int = 1000
    max_nodes: int = 10000
    render_batch_size: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_rotation_size: str = "10MB"
    log_retention_days: int = 30
    
    class Config:
        env_file = ".env"
        env_prefix = "MINDMAP_"

# Configuration factory
class ConfigFactory:
    @staticmethod
    def create_config(env: str = "development") -> AppConfig:
        if env == "production":
            return ProductionConfig()
        elif env == "testing":
            return TestingConfig()
        return DevelopmentConfig()
```

### 3. Service Layer Architecture

#### Core Services

```python
class MindMapService:
    def __init__(self, repository: MindMapRepository, config: AppConfig):
        self.repository = repository
        self.config = config
        self.cache = LRUCache(maxsize=config.cache_size)
    
    def create_node(self, node_data: NodeCreateRequest) -> Result[Node, Error]:
        # Business logic for node creation
        pass
    
    def update_node(self, node_id: int, updates: NodeUpdateRequest) -> Result[Node, Error]:
        # Business logic for node updates
        pass
    
    def delete_node(self, node_id: int) -> Result[bool, Error]:
        # Business logic for node deletion with cascade
        pass

class VisualizationService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.renderer_cache = {}
    
    def render_network(self, nodes: List[Node]) -> Result[str, Error]:
        # Optimized network rendering with caching
        pass
```

### 4. Event System Redesign

#### Event-Driven Architecture

```python
@dataclass
class Event:
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    source: str

class EventBus:
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        self.middleware: List[Callable] = []
    
    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def publish(self, event: Event) -> Result[bool, Error]:
        # Event publishing with middleware support
        pass

# Event handlers
class NodeEventHandler:
    def __init__(self, mindmap_service: MindMapService):
        self.mindmap_service = mindmap_service
    
    def handle_node_created(self, event: Event):
        # Handle node creation events
        pass
    
    def handle_node_updated(self, event: Event):
        # Handle node update events
        pass
```

### 5. Performance Optimization Strategy

#### Caching Layer

```python
class CacheManager:
    def __init__(self, config: AppConfig):
        self.node_cache = LRUCache(maxsize=config.cache_size)
        self.render_cache = LRUCache(maxsize=100)
        self.computation_cache = LRUCache(maxsize=500)
    
    def get_node(self, node_id: int) -> Optional[Node]:
        return self.node_cache.get(node_id)
    
    def cache_render(self, cache_key: str, html: str):
        self.render_cache[cache_key] = html
    
    def invalidate_node_cache(self, node_id: int):
        # Intelligent cache invalidation
        pass
```

#### Lazy Loading and Pagination

```python
class NodePaginator:
    def __init__(self, page_size: int = 50):
        self.page_size = page_size
    
    def get_page(self, nodes: List[Node], page: int) -> List[Node]:
        start = page * self.page_size
        end = start + self.page_size
        return nodes[start:end]
    
    def get_visible_nodes(self, all_nodes: List[Node], viewport: Viewport) -> List[Node]:
        # Return only nodes visible in current viewport
        pass
```

## Data Models

### Enhanced Node Model

```python
@dataclass
class Position:
    x: float
    y: float
    
    def distance_to(self, other: 'Position') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class Node:
    id: int
    label: str
    description: str
    position: Position
    urgency: UrgencyLevel
    tag: str
    parent_id: Optional[int]
    edge_type: EdgeType
    size: float
    color: str
    created_at: datetime
    updated_at: datetime
    
    def validate(self) -> List[ValidationError]:
        errors = []
        if not self.label.strip():
            errors.append(ValidationError("Label cannot be empty"))
        if self.position.x < -10000 or self.position.x > 10000:
            errors.append(ValidationError("X position out of bounds"))
        return errors
```

### Settings and Metadata

```python
@dataclass
class MindMapSettings:
    theme: str
    canvas_expanded: bool
    edge_length: int
    spring_strength: float
    size_multiplier: float
    color_mode: str
    custom_tags: List[str]
    custom_colors: Dict[str, str]

@dataclass
class MindMapMetadata:
    version: str
    created_at: datetime
    last_modified: datetime
    node_count: int
    backup_count: int
```

## Error Handling

### Comprehensive Error System

```python
class MindMapError(Exception):
    def __init__(self, message: str, error_code: str, context: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)

class ValidationError(MindMapError):
    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field})

class StorageError(MindMapError):
    def __init__(self, message: str, operation: str):
        super().__init__(message, "STORAGE_ERROR", {"operation": operation})

# Error handler
class ErrorHandler:
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None):
        # Centralized error handling with logging and user feedback
        pass
```

## Testing Strategy

### Test Architecture

```python
# Unit tests
class TestNodeService(unittest.TestCase):
    def setUp(self):
        self.mock_repository = Mock(spec=MindMapRepository)
        self.config = TestConfig()
        self.service = MindMapService(self.mock_repository, self.config)
    
    def test_create_node_success(self):
        # Test successful node creation
        pass
    
    def test_create_node_validation_error(self):
        # Test validation error handling
        pass

# Integration tests
class TestMindMapIntegration(unittest.TestCase):
    def setUp(self):
        self.test_db = create_test_database()
        self.app = create_test_app()
    
    def test_full_node_lifecycle(self):
        # Test complete node creation, update, deletion flow
        pass

# Performance tests
class TestPerformance(unittest.TestCase):
    def test_large_mindmap_loading(self):
        # Test performance with large datasets
        pass
```

### Test Data Management

```python
class TestDataFactory:
    @staticmethod
    def create_node(overrides: Dict[str, Any] = None) -> Node:
        defaults = {
            "id": 1,
            "label": "Test Node",
            "description": "Test Description",
            "position": Position(0, 0),
            "urgency": UrgencyLevel.MEDIUM,
            "tag": "test",
            "parent_id": None,
            "edge_type": EdgeType.DEFAULT
        }
        defaults.update(overrides or {})
        return Node(**defaults)
    
    @staticmethod
    def create_mindmap(node_count: int = 10) -> MindMapData:
        nodes = [TestDataFactory.create_node({"id": i}) for i in range(node_count)]
        return MindMapData(
            nodes=nodes,
            central_node_id=0,
            settings=MindMapSettings(),
            metadata=MindMapMetadata()
        )
```

## Migration Strategy

### Backward Compatibility

```python
class DataMigrator:
    def __init__(self, repository: MindMapRepository):
        self.repository = repository
        self.migrations = [
            Migration_v1_to_v2(),
            Migration_v2_to_v3(),
        ]
    
    def migrate(self, data: Dict[str, Any]) -> MindMapData:
        current_version = data.get("version", "1.0")
        
        for migration in self.migrations:
            if migration.should_apply(current_version):
                data = migration.apply(data)
                current_version = migration.target_version
        
        return MindMapData.from_dict(data)

class Migration_v1_to_v2:
    source_version = "1.0"
    target_version = "2.0"
    
    def should_apply(self, version: str) -> bool:
        return version == self.source_version
    
    def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Apply migration logic
        data["version"] = self.target_version
        return data
```

This design provides a solid foundation for implementing the improvements while maintaining backward compatibility and ensuring a smooth transition from the current architecture.