# MindMap Codebase Structure

## Overview

This is a Streamlit-based mind mapping application. The codebase has been refactored to improve maintainability, reduce code duplication, and standardize operations.

## Codebase Organization

The codebase is organized into the following modules:

### Core Modules

- **app.py** - Main Streamlit application entry point
- **src/state.py** - State management (global state, ideas, central node)
- **src/history.py** - Undo/redo functionality
- **src/message_format.py** - Message validation and formatting

### Utility Modules

- **src/utils.py** - General utility functions
- **src/node_utils.py** - Node-specific utilities
- **src/canvas_utils.py** - Canvas interaction utilities
- **src/position_utils.py** - Position update utilities
- **src/themes.py** - Theme definitions and visual styling

### Handler Modules

- **src/handlers.py** - Message handler registry and individual handler functions

## Refactoring Summary

The codebase has gone through multiple phases of refactoring:

### Phase 1: Consolidation of Duplicated Code

- Consolidated duplicated implementations of `collect_descendants` into a utility function
- Created node ID handling utilities (`normalize_node_id`, `compare_node_ids`, `find_node_by_id`)
- Developed a centralized position update service (`update_node_position_service`)
- Enhanced error handling in position update functions
- Moved coordinate conversion functions to utils.py

### Phase 2: Standardization

- Removed unused `normalize_node_id` function
- Standardized all node lookups with `find_node_by_id`
- Created a `find_closest_node` utility for canvas interactions
- Added a standardized `handle_error` utility for consistent error handling

### Phase 3: Input Validation and Response Standardization

- Added `validate_node_exists` to standardize node existence checks
- Created `validate_payload` for input validation
- Implemented `extract_canvas_coordinates` for standardized coordinate handling
- Added `standard_response` for consistent message responses
- Refactored handlers (select_node, center_node, edit_node, canvas handlers)

### Phase 4: Modular Architecture

- Extracted canvas-related utilities to a dedicated `canvas_utils.py` module
- Extracted position update utilities to a dedicated `position_utils.py` module
- Implemented a handler registry pattern to replace the large if-elif chain
- Standardized response creation across all handlers
- Simplified complex handler functions by extracting core logic to utility modules

## Best Practices Implemented

- **Single Responsibility Principle**: Each module has a clear, focused responsibility.
- **Consistent Error Handling**: Standardized error handling approach with proper logging.
- **Input Validation**: Consistent validation of input data before processing.
- **Standardized Responses**: Uniform response format for all message handlers.
- **Reduced Duplication**: Common operations extracted to utility functions.
- **Improved Type Safety**: Type hints and validation throughout the codebase.
- **Clear Function Names**: Self-explanatory function names that indicate purpose.
- **Modular Design**: Related functionality grouped into dedicated modules.
- **Handler Registry**: Dynamic handler registration instead of hard-coded logic.

## Future Improvements

Potential areas for further improvement:

1. Add comprehensive unit tests
2. Implement a more robust message bus architecture
3. Add data validation schemas (e.g., Pydantic models)
4. Improve documentation with docstrings
5. Consider a more formal dependency injection approach 