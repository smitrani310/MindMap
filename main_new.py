"""
Enhanced Mind Map Application - New Architecture Integration
Version 2.0 - Modernized with layered architecture

This version integrates the new service-oriented architecture while maintaining
compatibility with existing UI components.
"""

import logging
import traceback
import streamlit as st
from typing import Dict, Any, Optional

# Import the new service integration layer
from src.integration.service_adapter import init_service_adapter, get_service_adapter

# Import existing UI components (these will gradually be updated)
from src.ui.header import render_header
from src.ui.sidebar import render_sidebar
from src.ui.canvas import render_canvas
from src.ui.search import render_search
from src.ui.import_export import render_import_export
from src.ui.add_bubble import render_add_bubble_form
from src.ui.undo_redo import render_undo_redo
from src.ui.shortcuts import render_shortcuts
from src.ui.logs import render_logs_section
from src.ui.node_list import render_node_list, handle_node_list_actions
from src.ui.node_edit import render_node_edit_modal
from src.ui.tutorial import render_tutorial_prompt
from src.ui.node_details import render_node_details

# Import message handling (will be updated to use new architecture)
from src.message_handler import process_message_params, process_action

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_application():
    """Initialize the application with the new architecture."""
    try:
        # Initialize the service adapter
        adapter = init_service_adapter()
        
        # Set up Streamlit page configuration
        st.set_page_config(
            page_title="Enhanced Mind Map v2.0", 
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Store adapter in session state for UI components
        st.session_state['adapter'] = adapter
        
        logger.info("Application initialized successfully with new architecture")
        return adapter
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Failed to initialize application: {str(e)}")
        return None


def handle_legacy_state_compatibility():
    """Handle compatibility with legacy state management."""
    adapter = get_service_adapter()
    
    # Provide backward compatibility for components that expect old state structure
    if 'store' not in st.session_state:
        st.session_state['store'] = {}
    
    # Ensure settings exist in store
    if 'settings' not in st.session_state['store']:
        st.session_state['store']['settings'] = {
            'edge_length': 100,
            'spring_strength': 0.5,
            'size_multiplier': 1.0,
            'canvas_expanded': False,
            'color_mode': 'urgency',
            'custom_tags': [],
            'custom_colors': {
                'urgency': {
                    'high': '#FF5252',
                    'medium': '#FFC107',
                    'low': '#4CAF50'
                },
                'tags': {
                    'work': '#2196F3',
                    'personal': '#9C27B0',
                    'idea': '#00BCD4',
                    'task': '#FF9800',
                    'note': '#607D8B',
                    'important': '#F44336',
                    'question': '#8BC34A',
                    'research': '#3F51B5'
                }
            }
        }
    
    # Update store with current data for backward compatibility
    try:
        ideas = adapter.get_ideas()
        central = adapter.get_central()
        
        st.session_state['store'].update({
            'ideas': ideas,
            'central': central,
            'next_id': adapter.get_next_id(),
        })
        
    except Exception as e:
        logger.error(f"Error updating legacy state: {str(e)}")


def handle_ui_actions():
    """Handle UI actions using the new service layer."""
    adapter = get_service_adapter()
    
    # Handle center node action
    if 'center_node' in st.session_state:
        node_id = st.session_state.pop('center_node')
        logger.info(f"Attempting to center node {node_id}")
        if adapter.set_central(node_id):
            logger.info(f"Successfully centered node {node_id}")
            st.success(f"Centered node {node_id}")
            st.rerun()
        else:
            logger.error(f"Failed to center node {node_id}")
            st.error(f"Failed to center node {node_id}")
    
    # Handle delete node action
    if 'delete_node' in st.session_state:
        node_id = st.session_state.pop('delete_node')
        logger.info(f"Attempting to delete node {node_id}")
        if adapter.delete_node(node_id):
            logger.info(f"Successfully deleted node {node_id}")
            # Clear selected node if it was deleted
            if st.session_state.get('selected_node') == node_id:
                st.session_state['selected_node'] = None
            st.success(f"Deleted node {node_id}")
            st.rerun()
        else:
            logger.error(f"Failed to delete node {node_id}")
            st.error(f"Failed to delete node {node_id}")


def handle_message_processing():
    """Handle message processing with the new architecture."""
    try:
        # Process any messages from JavaScript (existing system)
        action, payload_str, current_time = process_message_params()
        
        if action:
            # Process the action using the existing system for now
            # TODO: Gradually migrate this to use the new service layer
            rerun_needed = process_action(action, payload_str, current_time)
            
            if rerun_needed:
                st.rerun()
                
    except Exception as e:
        logger.error(f"Error processing messages: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error processing messages: {str(e)}")


def render_application():
    """Render the main application UI."""
    try:
        # Update legacy state for backward compatibility
        handle_legacy_state_compatibility()
        
        # Render application header
        render_header()
        
        # Render sidebar with settings
        render_sidebar()
        
        # Render main canvas area
        render_canvas()
        
        # Render search functionality
        render_search()
        
        # Render import/export functionality
        render_import_export()
        
        # Render add bubble form
        render_add_bubble_form()
        
        # Render undo/redo buttons
        render_undo_redo()
        
        # Render keyboard shortcuts info
        render_shortcuts()
        
        # Render logs section
        render_logs_section()
        
        # Render node list and handle actions
        render_node_list()
        handle_node_list_actions()
        
        # Handle UI actions
        handle_ui_actions()
        
        # Render node edit modal
        render_node_edit_modal()
        
        # Render tutorial prompt when empty
        render_tutorial_prompt()
        
        # Render node details section
        render_node_details()
        
        # Handle message processing
        handle_message_processing()
        
    except Exception as e:
        logger.error(f"Error rendering application: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error rendering application: {str(e)}")


def display_architecture_info():
    """Display information about the new architecture."""
    with st.sidebar:
        with st.expander("🏗️ Architecture v2.0", expanded=False):
            st.markdown("""
            **New Architecture Features:**
            - ✅ Layered architecture (Domain, Application, Infrastructure)
            - ✅ Repository pattern for data access
            - ✅ Service layer for business logic
            - ✅ Comprehensive testing (100 tests)
            - ✅ Type safety and validation
            - ✅ Configuration management
            - ✅ Backup and restore functionality
            
            **Benefits:**
            - Improved maintainability
            - Better error handling
            - Enhanced testability
            - Scalable design
            """)
            
            # Show service statistics
            adapter = get_service_adapter()
            stats = adapter.get_statistics()
            
            st.markdown("**Current Statistics:**")
            st.json(stats)


def main():
    """Main application entry point."""
    try:
        # Initialize the application
        adapter = initialize_application()
        
        if adapter is None:
            st.error("Failed to initialize application. Please refresh the page.")
            return
        
        # Display architecture information
        display_architecture_info()
        
        # Render the main application
        render_application()
        
        # Display success message in sidebar
        with st.sidebar:
            st.success("✅ New Architecture Active")
            
    except Exception as e:
        logger.error(f"Unhandled exception in main: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Application error: {str(e)}")
        
        # Provide fallback information
        st.markdown("""
        ## Application Error
        
        The application encountered an error. This might be due to:
        - Missing dependencies
        - Configuration issues
        - Data corruption
        
        Please check the logs for more information.
        """)


if __name__ == "__main__":
    main()