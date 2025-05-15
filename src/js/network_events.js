/**
 * network_events.js - Handles canvas click, double-click, and context menu events
 * 
 * This file contains the event handlers for interaction with nodes in the network canvas.
 * It handles:
 * - Click events for selecting nodes
 * - Double-click events for editing nodes
 * - Context menu events for deleting nodes
 */

// Add a simplified click handler
document.addEventListener('DOMContentLoaded', function() {
    // Find the canvas container
    var networkDiv = document.getElementById('mynetwork');
    if (!networkDiv) {
        console.error('ERROR: mynetwork div not found');
        return;
    }
    
    // Add the global click handler
    networkDiv.addEventListener('click', function(event) {
        // Get coordinates relative to the container
        var rect = networkDiv.getBoundingClientRect();
        var relX = event.clientX - rect.left;
        var relY = event.clientY - rect.top;
        
        // Send the click event with coordinates
        simpleSendMessage('canvas_click', {
            x: relX,
            y: relY,
            canvasWidth: rect.width,
            canvasHeight: rect.height,
            timestamp: new Date().getTime()
        });
    });
    
    // Add double-click handler for editing
    networkDiv.addEventListener('dblclick', function(event) {
        // Get coordinates relative to the container
        var rect = networkDiv.getBoundingClientRect();
        var relX = event.clientX - rect.left;
        var relY = event.clientY - rect.top;
        
        // Send the double-click event
        simpleSendMessage('canvas_dblclick', {
            x: relX,
            y: relY,
            canvasWidth: rect.width,
            canvasHeight: rect.height,
            timestamp: new Date().getTime()
        });
        
        // Prevent default browser double-click behavior
        event.preventDefault();
    });
    
    // Add context menu handler for deleting
    networkDiv.addEventListener('contextmenu', function(event) {
        // Prevent default browser context menu
        event.preventDefault();
        
        // Get coordinates relative to the container
        var rect = networkDiv.getBoundingClientRect();
        var relX = event.clientX - rect.left;
        var relY = event.clientY - rect.top;
        
        // Confirm deletion
        if (confirm('Delete this bubble?')) {
            // Send the right-click event
            simpleSendMessage('canvas_contextmenu', {
                x: relX,
                y: relY,
                canvasWidth: rect.width,
                canvasHeight: rect.height,
                timestamp: new Date().getTime()
            });
        }
        
        return false;
    });
}); 