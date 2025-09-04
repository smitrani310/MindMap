"""
Simple Canvas Interaction System

This module provides a straightforward approach to canvas interactions
using basic Streamlit session state and simple JavaScript event handling.
"""

import streamlit as st
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def create_simple_canvas_html(network_html: str) -> str:
    """
    Create simple canvas HTML with basic interaction handling.
    
    Args:
        network_html: The PyVis network HTML
        
    Returns:
        Enhanced HTML with simple interaction handling
    """
    
    # Extract the body content from the network HTML
    body_start = network_html.find('<body')
    body_end = network_html.find('</body>') + 7
    
    if body_start == -1 or body_end == -1:
        # If no body tags found, use the whole content
        network_content = network_html
    else:
        network_content = network_html[body_start:body_end]
    
    # Create simple interaction HTML
    simple_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
            #interaction-status {{
                position: fixed;
                top: 10px;
                right: 10px;
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
                z-index: 1000;
                max-width: 300px;
            }}
            .status-success {{ background: rgba(76, 175, 80, 0.9) !important; }}
            .status-error {{ background: rgba(244, 67, 54, 0.9) !important; }}
            .status-info {{ background: rgba(33, 150, 243, 0.9) !important; }}
        </style>
    </head>
    {network_content}
    
    <div id="interaction-status">Ready for interactions...</div>
    
    <script>
    // Simple interaction system
    window.simpleCanvasInteraction = {{
        lastInteraction: null,
        
        showStatus: function(message, type = 'info') {{
            const status = document.getElementById('interaction-status');
            if (status) {{
                status.textContent = message;
                status.className = 'status-' + type;
                console.log('[CANVAS] ' + message);
                
                // Auto-hide after 3 seconds
                setTimeout(() => {{
                    status.textContent = 'Ready for interactions...';
                    status.className = '';
                }}, 3000);
            }}
        }},
        
        handleClick: function(event, actionType) {{
            const networkDiv = document.getElementById('mynetwork');
            if (!networkDiv) {{
                this.showStatus('Network container not found', 'error');
                return;
            }}
            
            const rect = networkDiv.getBoundingClientRect();
            const x = Math.round(event.clientX - rect.left);
            const y = Math.round(event.clientY - rect.top);
            
            const interaction = {{
                action: actionType,
                x: x,
                y: y,
                canvasWidth: Math.round(rect.width),
                canvasHeight: Math.round(rect.height),
                timestamp: Date.now()
            }};
            
            this.lastInteraction = interaction;
            this.showStatus(`${{actionType}} at (${{x}}, ${{y}})`, 'info');
            
            // Store in session storage for Streamlit to pick up
            try {{
                sessionStorage.setItem('canvas_interaction', JSON.stringify(interaction));
                sessionStorage.setItem('canvas_interaction_trigger', Date.now().toString());
                this.showStatus(`${{actionType}} recorded successfully`, 'success');
            }} catch (e) {{
                this.showStatus('Failed to record interaction: ' + e.message, 'error');
            }}
        }}
    }};
    
    // Set up event listeners when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {{
        console.log('Setting up simple canvas interactions...');
        
        // Wait for network to be ready
        let setupAttempts = 0;
        const maxAttempts = 20;
        
        function trySetupEvents() {{
            const networkDiv = document.getElementById('mynetwork');
            if (!networkDiv) {{
                setupAttempts++;
                if (setupAttempts < maxAttempts) {{
                    setTimeout(trySetupEvents, 500);
                }} else {{
                    console.error('Failed to find network container after', maxAttempts, 'attempts');
                }}
                return;
            }}
            
            console.log('Network container found, setting up events...');
            
            // Single click
            networkDiv.addEventListener('click', function(event) {{
                window.simpleCanvasInteraction.handleClick(event, 'canvas_click');
            }});
            
            // Double click
            networkDiv.addEventListener('dblclick', function(event) {{
                event.preventDefault();
                window.simpleCanvasInteraction.handleClick(event, 'canvas_dblclick');
            }});
            
            // Right click
            networkDiv.addEventListener('contextmenu', function(event) {{
                event.preventDefault();
                if (confirm('Delete node at this location?')) {{
                    window.simpleCanvasInteraction.handleClick(event, 'canvas_contextmenu');
                }}
                return false;
            }});
            
            // Drag end (for position updates)
            if (window.visNetwork) {{
                window.visNetwork.on('dragEnd', function(params) {{
                    if (params.nodes && params.nodes.length > 0) {{
                        const nodeId = params.nodes[0];
                        const positions = window.visNetwork.getPositions([nodeId]);
                        const position = positions[nodeId];
                        
                        if (position) {{
                            const dragInteraction = {{
                                action: 'node_drag',
                                nodeId: nodeId,
                                x: Math.round(position.x),
                                y: Math.round(position.y),
                                timestamp: Date.now()
                            }};
                            
                            sessionStorage.setItem('canvas_interaction', JSON.stringify(dragInteraction));
                            sessionStorage.setItem('canvas_interaction_trigger', Date.now().toString());
                            
                            window.simpleCanvasInteraction.showStatus(
                                `Node ${{nodeId}} moved to (${{Math.round(position.x)}}, ${{Math.round(position.y)}})`, 
                                'success'
                            );
                        }}
                    }}
                }});
                console.log('Drag handler set up successfully');
            }} else {{
                // Try to set up drag handler later
                setTimeout(function() {{
                    if (window.visNetwork) {{
                        // Same drag handler code as above
                        window.visNetwork.on('dragEnd', function(params) {{
                            if (params.nodes && params.nodes.length > 0) {{
                                const nodeId = params.nodes[0];
                                const positions = window.visNetwork.getPositions([nodeId]);
                                const position = positions[nodeId];
                                
                                if (position) {{
                                    const dragInteraction = {{
                                        action: 'node_drag',
                                        nodeId: nodeId,
                                        x: Math.round(position.x),
                                        y: Math.round(position.y),
                                        timestamp: Date.now()
                                    }};
                                    
                                    sessionStorage.setItem('canvas_interaction', JSON.stringify(dragInteraction));
                                    sessionStorage.setItem('canvas_interaction_trigger', Date.now().toString());
                                    
                                    window.simpleCanvasInteraction.showStatus(
                                        `Node ${{nodeId}} moved to (${{Math.round(position.x)}}, ${{Math.round(position.y)}})`, 
                                        'success'
                                    );
                                }}
                            }}
                        }});
                        console.log('Drag handler set up on retry');
                    }}
                }}, 2000);
            }}
            
            console.log('Simple canvas interactions set up successfully');
            window.simpleCanvasInteraction.showStatus('Canvas interactions ready!', 'success');
        }}
        
        // Start setup
        trySetupEvents();
    }});
    </script>
    </html>
    """
    
    return simple_html

def check_for_canvas_interactions() -> Optional[Dict[str, Any]]:
    """
    Check for canvas interactions stored in session state.
    
    Returns:
        Interaction data if found, None otherwise
    """
    # Check if we have interaction data in session state
    if 'canvas_interaction_data' in st.session_state:
        interaction_data = st.session_state.canvas_interaction_data
        
        # Clear it after reading
        del st.session_state.canvas_interaction_data
        
        logger.info(f"Found canvas interaction: {interaction_data.get('action', 'unknown')}")
        return interaction_data
    
    return None

def process_canvas_interaction(interaction: Dict[str, Any]) -> bool:
    """
    Process a canvas interaction.
    
    Args:
        interaction: The interaction data
        
    Returns:
        True if processed successfully, False otherwise
    """
    try:
        action = interaction.get('action')
        
        if not action:
            return False
        
        logger.info(f"Processing canvas interaction: {action}")
        
        if action in ['canvas_click', 'canvas_dblclick', 'canvas_contextmenu']:
            # Handle canvas coordinate-based interactions
            from src.events import handle_canvas_click
            
            payload = {
                'x': interaction.get('x', 0),
                'y': interaction.get('y', 0),
                'canvasWidth': interaction.get('canvasWidth', 800),
                'canvasHeight': interaction.get('canvasHeight', 600)
            }
            
            success = handle_canvas_click(payload, action)
            
            if success:
                st.success(f"✅ {action.replace('canvas_', '').title()} processed successfully!")
            else:
                st.warning(f"⚠️ {action.replace('canvas_', '').title()} - no node found at click position")
            
            return success
            
        elif action == 'node_drag':
            # Handle node position updates
            from src.events import handle_position_update
            
            payload = {
                'id': interaction.get('nodeId'),
                'x': interaction.get('x', 0),
                'y': interaction.get('y', 0)
            }
            
            success = handle_position_update(payload)
            
            if success:
                st.success(f"✅ Node position updated!")
            
            return success
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing canvas interaction: {e}")
        st.error(f"Error processing interaction: {e}")
        return False

def render_simple_canvas_interactions():
    """
    Render a simple interface for testing canvas interactions.
    """
    st.subheader("🎯 Canvas Interaction Status")
    
    # Check for interactions
    interaction = check_for_canvas_interactions()
    
    if interaction:
        st.info(f"**Last Interaction:** {interaction.get('action', 'unknown')} at ({interaction.get('x', 0)}, {interaction.get('y', 0)})")
        
        # Process the interaction
        success = process_canvas_interaction(interaction)
        
        if success:
            st.rerun()  # Refresh to show changes
    
    # Show interaction history
    if 'interaction_history' not in st.session_state:
        st.session_state.interaction_history = []
    
    if st.session_state.interaction_history:
        with st.expander("📋 Recent Interactions", expanded=False):
            for i, hist in enumerate(reversed(st.session_state.interaction_history[-5:])):
                st.write(f"**{len(st.session_state.interaction_history) - i}.** {hist}")
    
    # Manual test buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🖱️ Test Click"):
            test_interaction = {
                'action': 'canvas_click',
                'x': 100,
                'y': 100,
                'canvasWidth': 400,
                'canvasHeight': 300
            }
            st.session_state.canvas_interaction_data = test_interaction
            st.rerun()
    
    with col2:
        if st.button("🖱️🖱️ Test Double-Click"):
            test_interaction = {
                'action': 'canvas_dblclick',
                'x': 150,
                'y': 150,
                'canvasWidth': 400,
                'canvasHeight': 300
            }
            st.session_state.canvas_interaction_data = test_interaction
            st.rerun()
    
    with col3:
        if st.button("🗑️ Clear History"):
            st.session_state.interaction_history = []
            st.success("History cleared!")
            st.rerun()

# JavaScript component for session storage polling
def create_session_storage_poller() -> str:
    """Create JavaScript to poll session storage for interactions."""
    return """
    <script>
    // Poll session storage for interactions
    function pollSessionStorage() {
        try {
            const interactionData = sessionStorage.getItem('canvas_interaction');
            const trigger = sessionStorage.getItem('canvas_interaction_trigger');
            
            if (interactionData && trigger) {
                const interaction = JSON.parse(interactionData);
                
                // Send to Streamlit via a simple form submission
                const form = document.createElement('form');
                form.method = 'POST';
                form.style.display = 'none';
                
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'canvas_interaction';
                input.value = interactionData;
                
                form.appendChild(input);
                document.body.appendChild(form);
                
                // Clear session storage
                sessionStorage.removeItem('canvas_interaction');
                sessionStorage.removeItem('canvas_interaction_trigger');
                
                // Trigger Streamlit update by modifying the page
                if (window.parent && window.parent.postMessage) {
                    window.parent.postMessage({
                        type: 'canvas_interaction',
                        data: interaction
                    }, '*');
                }
                
                console.log('Interaction sent to Streamlit:', interaction);
            }
        } catch (e) {
            console.error('Error polling session storage:', e);
        }
    }
    
    // Poll every 500ms
    setInterval(pollSessionStorage, 500);
    
    // Also poll immediately
    pollSessionStorage();
    </script>
    """