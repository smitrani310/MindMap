"""Logs section component for the Enhanced Mind Map application."""

import os
import streamlit as st
from src.logging_setup import create_new_log

def render_logs_section():
    """
    Render the logs section in the sidebar.
    """
    logs_dir = "logs"
    
    with st.sidebar.expander("📊 Logs"):
        st.write("**Current Session Log:**")
        
        # Get list of log files
        log_files = []
        if os.path.exists(logs_dir):
            log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith('.log')], reverse=True)
        
        if log_files:
            # Show current log file
            current_log = log_files[0]
            st.caption(f"Current: {current_log}")
            
            # Add button to create new log
            if st.button("Create New Log"):
                new_log = create_new_log()
                st.success(f"Created new log file: {new_log}")
                st.rerun()
            
            # Option to view the current log
            if st.button("View Current Log"):
                try:
                    with open(os.path.join(logs_dir, current_log), 'r') as f:
                        log_content = f.read()
                    st.text_area("Log Content", log_content, height=300)
                except Exception as e:
                    st.error(f"Error reading log file: {str(e)}")
            
            # Download current log
            try:
                with open(os.path.join(logs_dir, current_log), 'r') as f:
                    log_content = f.read()
                    st.download_button(
                        "💾 Download Current Log",
                        log_content,
                        file_name=current_log,
                        mime="text/plain",
                        key="download_current_log"
                    )
            except Exception as e:
                st.error(f"Error preparing log for download: {str(e)}")
            
            # Previous logs dropdown
            if len(log_files) > 1:
                st.write("**Previous Session Logs:**")
                selected_log = st.selectbox(
                    "Select log file",
                    options=log_files[1:],
                    format_func=lambda x: f"{x.replace('mindmap_session_', '').replace('.log', '')}"
                )
                
                if selected_log:
                    # View selected log
                    if st.button("View Selected Log"):
                        try:
                            with open(os.path.join(logs_dir, selected_log), 'r') as f:
                                log_content = f.read()
                            st.text_area("Previous Log Content", log_content, height=300)
                        except Exception as e:
                            st.error(f"Error reading selected log: {str(e)}")
                    
                    # Download selected log
                    try:
                        with open(os.path.join(logs_dir, selected_log), 'r') as f:
                            log_content = f.read()
                            st.download_button(
                                "💾 Download Selected Log",
                                log_content,
                                file_name=selected_log,
                                mime="text/plain",
                                key="download_selected_log"
                            )
                    except Exception as e:
                        st.error(f"Error preparing selected log for download: {str(e)}")
        else:
            st.info("No log files found.") 