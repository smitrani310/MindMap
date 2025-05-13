# Enhanced Mind Map

A powerful, interactive mind mapping application built with Streamlit and PyVis. This application allows you to create, organize, and visualize your ideas in a dynamic and intuitive way.

## Features

### Core Functionality
- **Interactive Node Creation**: Add, edit, and delete nodes with ease
- **Hierarchical Organization**: Create parent-child relationships between nodes
- **Visual Customization**: 
  - Multiple themes (light/dark mode)
  - Customizable node colors based on tags and urgency
  - Adjustable connection lengths and strengths
  - Size variations based on urgency levels
- **Data Persistence**: All changes are automatically saved to a JSON file
- **Position Persistence**: Node positions are correctly maintained across sessions
- **Error Handling**: Comprehensive error handling and logging system

### Advanced Features
- **Tag System**: Categorize nodes with color-coded tags
- **Urgency Levels**: Prioritize nodes with different urgency settings
- **Node Descriptions**: Add detailed notes to each node
- **Connection Types**: Different visual styles for different types of relationships
- **Search Functionality**: 
  - Search across all nodes
  - Search and replace functionality
  - Filter nodes in the sidebar
- **Undo/Redo**: Full history of changes with undo/redo capability
- **Import/Export**: Save and load your mind maps as JSON files
- **Canvas Expansion**: Toggle between normal and expanded view modes

### Interactive Controls
- **Keyboard Shortcuts**:
  - Double-click: Edit node
  - Right-click: Delete node
  - Drag: Move node
  - Drag near another: Change parent
  - Ctrl+Z: Undo
  - Ctrl+Y: Redo
  - Ctrl+Space: Center selected node
- **Sidebar Controls**:
  - Theme selection
  - Connection length adjustment
  - Spring strength adjustment
  - Urgency size impact adjustment
  - Node list with filtering
  - Import/Export functionality

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/enhanced-mindmap.git
cd enhanced-mindmap
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
streamlit run Main.py
```

Or use the provided runner script with enhanced position persistence:
```bash
python run_app_with_position_fix.py
```

2. Open your web browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

3. Start creating your mind map:
   - Use the "Add Bubble" form in the sidebar to create new nodes
   - Double-click nodes to edit them
   - Drag nodes to reposition them
   - Use the settings panel to customize the appearance
   - Export your mind map when finished

## Verification Tools

The application includes several tools to verify node position persistence:

1. **Position Fix Verification Script**:
```bash
python -m tests.verify_position_fix
```
This script creates test nodes, updates their positions, and verifies they are saved correctly.

2. **JavaScript Console Debug Tools**:
- Track a node's position: `window.positionDebug.trackNode(nodeId)`
- Check position history: `window.positionDebug.getDebugInfo(nodeId)`
- Get current position: `window.positionDebug.getCurrentPosition(nodeId)`

3. **Data File Inspector**:
```bash
python -m tests.inspect_data_file
```
Examines the data file to verify position storage.

## Project Structure

```
enhanced-mindmap/
├── Main.py                   # Main application file
├── run_app_with_position_fix.py  # Runner with position fixes
├── mindmap_data.json         # Data persistence file
├── requirements.txt          # Project dependencies
├── src/
│   ├── config.py             # Configuration settings
│   ├── state.py              # State management
│   ├── history.py            # Undo/redo functionality
│   ├── utils.py              # Utility functions
│   ├── themes.py             # Theme definitions
│   ├── handlers.py           # Event handlers
│   ├── node_utils.py         # Node management utilities
│   ├── message_format.py     # Message format definitions
│   ├── message_utils.js      # JavaScript message utilities
│   └── network_handlers.js   # JavaScript interaction handlers
├── tests/
│   ├── debug_position_flow.py # Position update flow debugger
│   ├── inspect_data_file.py   # Data file inspector
│   ├── verify_position_fix.py # Position fix verification
│   ├── POSITION_FIX_README.md # Position fix documentation
│   └── other test files...
└── README.md                 # This file
```

## Dependencies

- streamlit
- pyvis
- typing
- json
- datetime
- os
- logging

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Version History

- v5.5: Position Persistence Fix
  - Fixed node position persistence across sessions
  - Added robust position validation and verification tools
  - Improved dragEnd event handling
  - Enhanced position debugging capabilities

- v5.4: Enhanced Mind Map with Improved Structure
  - Added centralized configuration
  - Separated JavaScript handlers
  - Improved error handling
  - Better code organization
  
- v5.3: Enhanced Mind Map with Stability Improvements
  - Added data persistence with JSON file storage
  - Added expanded canvas option
  - Improved node search in sidebar
  - Fixed interaction on Windows/Chrome
  - Cleaned up code structure 