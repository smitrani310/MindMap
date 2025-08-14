"""Integration layer for bridging old and new architecture."""

from .service_adapter import (
    ServiceAdapter,
    get_service_adapter,
    init_service_adapter,
    # Backward compatibility functions
    get_ideas,
    get_central,
    get_next_id,
    set_central,
    add_idea,
    set_ideas,
    find_node_by_id,
)

__all__ = [
    "ServiceAdapter",
    "get_service_adapter",
    "init_service_adapter",
    "get_ideas",
    "get_central", 
    "get_next_id",
    "set_central",
    "add_idea",
    "set_ideas",
    "find_node_by_id",
]