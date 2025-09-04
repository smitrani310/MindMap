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
    from src.application.app_lifecycle import get_lifecycle_manager
    
    try:
        # Use the lifecycle manager for initialization
        manager = get_lifecycle_manager()
        success = manager.initialize()
        
        if success:
            logger.info("Application initialized successfully with new architecture")
            return manager.get_adapter()
        else:
            logger.error("Failed to initialize application through lifecycle manager")
            st.error("Failed to initialize application. Please refresh the page.")
            return None
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Failed to initialize application: {str(e)}")
        return None


def handle_legacy_state_compatibility():
    """Handle compatibility with legacy state management."""
    from src.application.app_lifecycle import get_lifecycle_manager
    
    try:
        manager = get_lifecycle_manager()
        manager.update_legacy_compatibility()
        
    except Exception as e:
        logger.error(f"Error updating legacy state: {str(e)}")
        # Provide fallback state if lifecycle manager fails
        if 'store' not in st.session_state:
            st.session_state['store'] = {
                'ideas': [],
                'central': None,
                'next_id': 1,
                'settings': {
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
            }


def handle_ui_actions():
    """Handle UI actions using the lifecycle manager."""
    from src.application.app_lifecycle import get_lifecycle_manager
    
    try:
        manager = get_lifecycle_manager()
        manager.process_ui_actions()
        
    except Exception as e:
        logger.error(f"Error processing UI actions: {str(e)}")
        st.error("Error processing UI action. Please try again.")


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
    from src.application.app_lifecycle import get_lifecycle_manager
    
    with st.sidebar:
        with st.expander("🏗️ Architecture v2.0", expanded=False):
            st.markdown("""
            **New Architecture Features:**
            - ✅ Layered architecture (Domain, Application, Infrastructure)
            - ✅ Repository pattern for data access
            - ✅ Service layer for business logic
            - ✅ Comprehensive testing (114+ tests)
            - ✅ Type safety and validation
            - ✅ Configuration management
            - ✅ Backup and restore functionality
            - ✅ Application lifecycle management
            - ✅ Performance monitoring
            
            **Benefits:**
            - Improved maintainability
            - Better error handling
            - Enhanced testability
            - Scalable design
            - Centralized lifecycle management
            """)
            
            # Show comprehensive statistics
            try:
                manager = get_lifecycle_manager()
                stats = manager.get_statistics()
                
                st.markdown("**Current Statistics:**")
                
                # Display basic stats
                if 'total_nodes' in stats:
                    st.metric("Total Nodes", stats['total_nodes'])
                
                if 'urgency_distribution' in stats:
                    st.markdown("**Urgency Distribution:**")
                    for urgency, count in stats['urgency_distribution'].items():
                        st.write(f"- {urgency.title()}: {count}")
                
                # Display performance stats if available
                if 'performance' in stats and stats['performance']:
                    st.markdown("**Performance:**")
                    perf = stats['performance']
                    if 'operations_count' in perf:
                        st.metric("Operations", perf['operations_count'])
                
            except Exception as e:
                logger.error(f"Error displaying statistics: {str(e)}")
                st.error("Unable to load statistics")


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