# Canvas Refactoring

## Overview
We've consolidated all canvas-related functionality into a dedicated module to improve maintainability and organization.

## Changes Made

### 1. Created a New Canvas Module (`src/ui/canvas.py`)
- Created a central module for all canvas functionality
- Moved canvas toggle functionality from `src/ui/canvas_toggle.py`
- Moved canvas interaction handlers from `src/canvas_utils.py`
- Added canvas utility functions for coordinate handling and calculations
- Added integration with network visualization

### 2. Modular Design with Specific Functions
- `render_canvas()`: Main entry point for canvas rendering (high-level)
- `render_canvas_toggle()`: Handles canvas expansion/collapse functionality
- `handle_canvas_interaction()`: Processes click, dblclick, and contextmenu events
- Utility functions for canvas dimensions and coordinate transformations

### 3. Updated Dependent Modules
- Updated `main.py` to use the new canvas module
- Updated `handlers.py` to use the new canvas module
- Updated `src/ui/__init__.py` to expose the new canvas module
- Documented deprecated modules that can be removed

## Benefits
- **Centralized Canvas Logic**: All canvas functionality is now in one place
- **Improved Organization**: Clear separation between canvas and network visualization
- **Better Code Structure**: Logical grouping of related functionality
- **Enhanced Maintainability**: Changes to canvas behavior only affect one module
- **Cleaner Main Application**: Main.py is now more concise and focused

## Architecture
The new flow for canvas-related functionality:

1. Main app calls `render_canvas()`
2. Canvas module handles toggle functionality via `render_canvas_toggle()`
3. Canvas module integrates with network visualization
4. Canvas module exposes utility functions for canvas interactions
5. Handlers use canvas module for event processing

## Files Modified
- `src/ui/canvas.py` (new)
- `main.py`
- `src/handlers.py`
- `src/ui/__init__.py`

## Files Deprecated
- `src/ui/canvas_toggle.py`
- `src/canvas_utils.py` 