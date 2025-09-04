"""
Application lifecycle management for the Enhanced Mind Map application.

This module handles application initialization, configuration, and cleanup
in a centralized manner.
"""

import logging
import streamlit as st
from typing import Optional, Dict, Any
import traceback

from src.integration.service_adapter import ServiceAdapter, init_service_adapter, get_service_adapter
from src.infrastructure.performance import get_performance_monitor
from src.infrastructure.cache import get_cache_manager


logger = logging.getLogger(__name__)


class ApplicationLifecycleManager:
    """Manages the application lifecycle from initialization to cleanup."""
    
    def __init__(self):
        self.adapter: Optional[ServiceAdapter] = None
        self.performance_monitor = get_performance_monitor()
        self.cache_manager = get_cache_manager()
        self.initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the application with all required components.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            logger.info("Starting application initialization...")
            
            # Configure Streamlit page
            self._configure_streamlit()
            
            # Initialize service adapter
            self.adapter = init_service_adapter()
            
            # Set up session state
            self._setup_session_state()
            
            # Initialize performance monitoring (no session start needed)
            logger.debug("Performance monitoring initialized")
            
            self.initialized = True
            logger.info("Application initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _configure_streamlit(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Enhanced Mind Map v2.0", 
            layout="wide",
            initial_sidebar_state="expanded",
            page_icon="🧠"
        )
    
    def _setup_session_state(self):
        """Set up session state variables."""
        if 'app_lifecycle' not in st.session_state:
            st.session_state['app_lifecycle'] = self
        
        if 'adapter' not in st.session_state:
            st.session_state['adapter'] = self.adapter
        
        # Initialize other session state variables
        if 'selected_node' not in st.session_state:
            st.session_state['selected_node'] = None
        
        if 'ui_state' not in st.session_state:
            st.session_state['ui_state'] = {
                'show_tutorial': False,
                'show_logs': False,
                'canvas_height': '600px'
            }
    
    def get_adapter(self) -> ServiceAdapter:
        """Get the service adapter instance."""
        if not self.initialized or self.adapter is None:
            raise RuntimeError("Application not properly initialized")
        return self.adapter
    
    def handle_error(self, error: Exception, context: str = ""):
        """
        Handle application errors in a centralized way.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
        """
        error_msg = f"Application error{' in ' + context if context else ''}: {str(error)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Show user-friendly error message
        st.error(f"An error occurred{' in ' + context if context else ''}. Please try again or refresh the page.")
        
        # Log performance impact
        self.performance_monitor.record_metric(
            operation="error_handling",
            duration_ms=0,
            success=False,
            error=error_msg
        )
    
    def update_legacy_compatibility(self):
        """Update session state for backward compatibility with existing UI components."""
        if not self.initialized:
            return
        
        try:
            # Get current data from service adapter
            ideas = self.adapter.get_ideas()
            central = self.adapter.get_central()
            settings = self.adapter.get_settings()
            
            # Update session state store for backward compatibility
            if 'store' not in st.session_state:
                st.session_state['store'] = {}
            
            st.session_state['store'].update({
                'ideas': ideas,
                'central': central,
                'next_id': self.adapter.get_next_id(),
                'settings': settings
            })
            
            logger.debug(f"Updated legacy compatibility state with {len(ideas)} ideas")
            
        except Exception as e:
            logger.error(f"Error updating legacy compatibility: {str(e)}")
    
    def process_ui_actions(self):
        """Process UI actions that require service layer interaction."""
        if not self.initialized:
            return
        
        try:
            # Handle center node action
            if 'center_node' in st.session_state:
                node_id = st.session_state.pop('center_node')
                self._handle_center_node(node_id)
            
            # Handle delete node action
            if 'delete_node' in st.session_state:
                node_id = st.session_state.pop('delete_node')
                self._handle_delete_node(node_id)
            
            # Handle bulk operations
            if 'bulk_operation' in st.session_state:
                operation = st.session_state.pop('bulk_operation')
                self._handle_bulk_operation(operation)
                
        except Exception as e:
            self.handle_error(e, "UI action processing")
    
    def _handle_center_node(self, node_id: int):
        """Handle centering a node."""
        logger.info(f"Processing center node action for node {node_id}")
        
        if self.adapter.set_central(node_id):
            logger.info(f"Successfully centered node {node_id}")
            st.success(f"Centered node {node_id}")
            st.rerun()
        else:
            logger.error(f"Failed to center node {node_id}")
            st.error(f"Failed to center node {node_id}")
    
    def _handle_delete_node(self, node_id: int):
        """Handle deleting a node."""
        logger.info(f"Processing delete node action for node {node_id}")
        
        if self.adapter.delete_node(node_id):
            logger.info(f"Successfully deleted node {node_id}")
            # Clear selected node if it was deleted
            if st.session_state.get('selected_node') == node_id:
                st.session_state['selected_node'] = None
            st.success(f"Deleted node {node_id}")
            st.rerun()
        else:
            logger.error(f"Failed to delete node {node_id}")
            st.error(f"Failed to delete node {node_id}")
    
    def _handle_bulk_operation(self, operation: Dict[str, Any]):
        """Handle bulk operations."""
        operation_type = operation.get('type')
        logger.info(f"Processing bulk operation: {operation_type}")
        
        if operation_type == 'import':
            self._handle_bulk_import(operation.get('data', []))
        elif operation_type == 'export':
            self._handle_bulk_export()
        else:
            logger.warning(f"Unknown bulk operation type: {operation_type}")
    
    def _handle_bulk_import(self, data: list):
        """Handle bulk import operation."""
        try:
            success = self.adapter.set_ideas(data)
            if success:
                st.success(f"Successfully imported {len(data)} nodes")
                st.rerun()
            else:
                st.error("Failed to import data")
        except Exception as e:
            self.handle_error(e, "bulk import")
    
    def _handle_bulk_export(self):
        """Handle bulk export operation."""
        try:
            ideas = self.adapter.get_ideas()
            # Store export data in session state for download
            st.session_state['export_data'] = ideas
            st.success(f"Prepared {len(ideas)} nodes for export")
        except Exception as e:
            self.handle_error(e, "bulk export")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get application statistics."""
        if not self.initialized:
            return {}
        
        try:
            stats = self.adapter.get_statistics()
            
            # Add performance statistics
            perf_stats = self.performance_monitor.get_all_stats()
            stats.update({
                'performance': perf_stats,
                'cache_stats': self.cache_manager.get_stats() if hasattr(self.cache_manager, 'get_stats') else {}
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}
    
    def cleanup(self):
        """Clean up resources when the application shuts down."""
        try:
            if self.performance_monitor:
                # Log performance summary before cleanup
                from src.infrastructure.performance import log_performance_summary
                log_performance_summary()
            
            if self.cache_manager:
                # Clear temporary caches
                pass
            
            logger.info("Application cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


# Global lifecycle manager instance
_lifecycle_manager: Optional[ApplicationLifecycleManager] = None


def get_lifecycle_manager() -> ApplicationLifecycleManager:
    """Get the global application lifecycle manager."""
    global _lifecycle_manager
    
    if _lifecycle_manager is None:
        _lifecycle_manager = ApplicationLifecycleManager()
    
    return _lifecycle_manager


def initialize_application() -> bool:
    """Initialize the application using the lifecycle manager."""
    manager = get_lifecycle_manager()
    return manager.initialize()


def get_application_adapter() -> ServiceAdapter:
    """Get the service adapter from the lifecycle manager."""
    manager = get_lifecycle_manager()
    return manager.get_adapter()