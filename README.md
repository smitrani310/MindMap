# 🧠 Enhanced Mind Map

A feature-rich, interactive mind map app built with Streamlit and PyVis.

## Features

- Add, edit, and delete nodes (bubbles)
- Parent-child relationships (drag to reparent)
- Tags, urgency, and descriptions for nodes
- Undo/redo functionality
- Custom themes and color coding
- Import/export mind maps as JSON
- Keyboard shortcuts for power users

## Project Structure

```
MindMap/
├── mindmap_app_v5.2_claude.py      # Main Streamlit app
├── requirements.txt
├── README.md
├── src/                            # Core logic modules
├── components/                     # (Optional) Custom JS components
├── static/                         # (Optional) Images, icons, CSS
├── data/                           # (Optional) Example data, exports
└── tests/                          # (Optional) Unit tests
```

## Getting Started

1. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Run the app:**
    ```bash
    streamlit run mindmap_app_v5.2_claude.py
    ```

3. **Open your browser:**  
   Visit [http://localhost:8501](http://localhost:8501)

## Usage

- Use the sidebar to add, edit, or search nodes.
- Drag nodes to reposition or reparent.
- Double-click a node to edit, right-click to delete.
- Use keyboard shortcuts (Ctrl+Z, Ctrl+Y, Ctrl+N) for quick actions.
- Import/export your mind map as JSON.

## Customization

- Themes and tags can be edited in `src/themes.py`.
- Logic is modularized in the `src/` directory for easy extension.

## License

MIT 