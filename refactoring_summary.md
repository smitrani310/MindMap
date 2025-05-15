# Event Handling Refactoring

## Overview
We've extracted event handling logic from the monolithic application into separate modules for improved maintainability and organization.

## Changes Made

### 1. Created a New Events Module (`src/events.py`)
- Created a dedicated module to handle all UI and canvas events
- Extracted canvas click, double-click, and context menu event handlers
- Extracted node position update handler
- Ensured proper error handling and logging

### 2. Updated Message Handler (`src/message_handler.py`)
- Streamlined to focus on message processing and routing
- Removed duplicated event handling code
- Now imports and calls dedicated event handlers from the events module
- Improved separation of concerns:
  - Message parsing/parameter extraction
  - Message routing
  - Action processing

### 3. Updated Main Application (`main.py`)
- Removed duplicated message handling code
- Updated imports to use the new modules
- Simplified the flow of handling UI events
- Replaced verbose message handling code with clean function calls

## Benefits
- **Improved Maintainability**: Easier to update event handling logic in isolated modules
- **Better Code Organization**: Separation of concerns between message handling and event processing
- **Reduced Duplication**: Event handling logic now exists in only one place
- **Simplified Main Application**: Main.py is now more focused on application structure and less on implementation details
- **Enhanced Testability**: Event handlers can be tested independently

## Architecture
The new flow for handling events:

1. UI Event (JavaScript) → URL Parameters
2. `main.py` calls `process_message_params()` from message_handler
3. `process_action()` routes the action to appropriate handler
4. Event handlers in `events.py` process specific actions
5. UI is updated based on event results 