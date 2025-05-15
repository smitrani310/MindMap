/**
 * position_tracking.js - Handles node position tracking and persistence
 * 
 * This file contains functionality for:
 * - Tracking node positions during drag events
 * - Applying stored positions to nodes on page load
 * - Testing position persistence
 * - Debugging position-related issues
 */

// Store node positions from the server
window.serverNodePositions = {}; 

// Position tracking debug object
window.positionDebug = {
    trackNodes: {},
    
    // Start tracking a node's position
    trackNode: function(nodeId) {
        if (!nodeId) return;
        
        this.trackNodes[nodeId] = {
            id: nodeId,
            lastPosition: null,
            history: []
        };
        
        console.log(`🔍 Started tracking position for node ${nodeId}`);
        return true;
    },
    
    // Update a tracked node's position (called automatically by the tracking interval)
    updateNodePosition: function(nodeId) {
        if (!this.trackNodes[nodeId] || !window.visNetwork) return;
        
        try {
            const positions = window.visNetwork.getPositions([nodeId]);
            const position = positions[nodeId];
            
            if (!position) return;
            
            // Store position
            const tracker = this.trackNodes[nodeId];
            
            // Only record if position has changed
            if (!tracker.lastPosition || 
                tracker.lastPosition.x !== position.x || 
                tracker.lastPosition.y !== position.y) {
                
                // Add to history
                tracker.history.push({
                    timestamp: Date.now(),
                    x: position.x,
                    y: position.y,
                    source: 'auto_check'
                });
                
                // Update last position
                tracker.lastPosition = { x: position.x, y: position.y };
                
                console.log(`🔍 Node ${nodeId} position updated to (${position.x}, ${position.y})`);
            }
        } catch (e) {
            console.error(`Error tracking node ${nodeId} position:`, e);
        }
    },
    
    // Record position update event from dragEnd
    recordDragEvent: function(nodeId, x, y) {
        if (!this.trackNodes[nodeId]) {
            this.trackNode(nodeId);
        }
        
        const tracker = this.trackNodes[nodeId];
        tracker.lastPosition = { x: x, y: y };
        tracker.history.push({
            timestamp: Date.now(),
            x: x,
            y: y,
            source: 'drag_end'
        });
        
        console.log(`🔍 Node ${nodeId} dragged to (${x}, ${y})`);
    },
    
    // Get debugging info
    getDebugInfo: function(nodeId) {
        if (!nodeId) {
            return this.trackNodes;
        }
        
        return this.trackNodes[nodeId] || null;
    },
    
    // Get current position from vis.js
    getCurrentPosition: function(nodeId) {
        if (!window.visNetwork) return null;
        
        try {
            const positions = window.visNetwork.getPositions([nodeId]);
            return positions[nodeId];
        } catch (e) {
            console.error(`Error getting position for node ${nodeId}:`, e);
            return null;
        }
    },
    
    // Run a diagnostic test for node position persistence
    testPositionPersistence: function(nodeId) {
        if (!nodeId || !window.visNetwork) {
            console.error("Cannot test: Missing nodeId or visNetwork");
            return {success: false, error: "Missing nodeId or visNetwork"};
        }
        
        try {
            // Get current position
            const currentPos = this.getCurrentPosition(nodeId);
            if (!currentPos) {
                return {success: false, error: "Node not found in network"};
            }
            
            console.log(`Current position of node ${nodeId}: (${currentPos.x}, ${currentPos.y})`);
            
            // Modify position slightly
            const newX = currentPos.x + 50;
            const newY = currentPos.y + 50;
            
            // Update position via network
            window.visNetwork.moveNode(nodeId, newX, newY);
            console.log(`Moved node ${nodeId} to (${newX}, ${newY})`);
            
            // Manually trigger position update
            const result = window.directParentCommunication.sendMessage('pos', {
                id: nodeId,
                x: newX,
                y: newY
            });
            
            // Show update result
            console.log(`Position update sent: ${result ? "SUCCESS" : "FAILED"}`);
            
            // Store test data
            const testData = {
                nodeId: nodeId,
                originalPosition: currentPos,
                newPosition: {x: newX, y: newY},
                updateSent: result,
                timestamp: new Date().toISOString()
            };
            
            // Store test data in localStorage for verification after reload
            try {
                localStorage.setItem('position_test_data', JSON.stringify(testData));
            } catch(e) {
                console.error("Could not save test data:", e);
            }
            
            return {
                success: true,
                message: "Position update test completed. Reload page to verify persistence.",
                testData: testData
            };
        } catch(e) {
            console.error("Position persistence test failed:", e);
            return {success: false, error: e.message};
        }
    },
    
    // Verify persistence after page reload
    verifyPersistence: function() {
        try {
            // Get stored test data
            const testDataStr = localStorage.getItem('position_test_data');
            if (!testDataStr) {
                return {success: false, message: "No test data found. Run testPositionPersistence first."};
            }
            
            const testData = JSON.parse(testDataStr);
            const nodeId = testData.nodeId;
            
            // Get current position after reload
            if (!window.visNetwork) {
                return {success: false, message: "Network not available yet. Try again in a moment."};
            }
            
            const currentPos = this.getCurrentPosition(nodeId);
            if (!currentPos) {
                return {success: false, message: "Node not found after reload"};
            }
            
            // Check if position was maintained
            const expectedX = testData.newPosition.x;
            const expectedY = testData.newPosition.y;
            const currentX = currentPos.x;
            const currentY = currentPos.y;
            
            // Calculate difference (allowing small floating point variations)
            const xDiff = Math.abs(expectedX - currentX);
            const yDiff = Math.abs(expectedY - currentY);
            
            const success = xDiff < 1 && yDiff < 1;
            
            if (success) {
                console.log(`✅ POSITION PERSISTENCE TEST PASSED! Node ${nodeId} maintained position (${currentX}, ${currentY})`);
            } else {
                console.error(`❌ POSITION PERSISTENCE TEST FAILED! 
                    Expected: (${expectedX}, ${expectedY})
                    Actual: (${currentX}, ${currentY})
                    Diff: (${xDiff}, ${yDiff})`);
            }
            
            return {
                success: success,
                message: success ? "Position successfully maintained!" : "Position not maintained correctly",
                expected: testData.newPosition,
                actual: currentPos,
                diff: {x: xDiff, y: yDiff}
            };
        } catch(e) {
            console.error("Verification failed:", e);
            return {success: false, error: e.message};
        }
    }
};

// Function to explicitly ensure positions from server data are applied to nodes
function ensureNodePositionsApplied() {
    if (window.visNetwork && window.serverNodePositions) {
        console.log('🔧 Explicitly applying stored positions to network');
        
        try {
            if (typeof applyStoredPositions === 'function') {
                // Use the dedicated function if available
                applyStoredPositions(window.visNetwork, window.serverNodePositions);
            } else {
                // Manual fallback
                console.log('📝 Using manual position application');
                const nodeIds = Object.keys(window.serverNodePositions);
                console.log(`Applying positions to ${nodeIds.length} nodes`);
                
                let appliedCount = 0;
                nodeIds.forEach(nodeId => {
                    const pos = window.serverNodePositions[nodeId];
                    if (pos && pos.x !== undefined && pos.y !== undefined) {
                        try {
                            const x = parseFloat(pos.x);
                            const y = parseFloat(pos.y);
                            
                            if (!isNaN(x) && !isNaN(y)) {
                                window.visNetwork.moveNode(nodeId, x, y);
                                appliedCount++;
                            }
                        } catch (e) {
                            console.error(`Error applying position to node ${nodeId}:`, e);
                        }
                    }
                });
                
                console.log(`Manually applied ${appliedCount} node positions`);
            }
            
            // Force network to redraw
            if (window.visNetwork.redraw) {
                window.visNetwork.redraw();
            }
            
            console.log('✅ Node positions applied successfully');
            return true;
        } catch (error) {
            console.error('❌ Error applying node positions:', error);
            return false;
        }
    } else {
        console.warn('⚠️ Cannot apply positions: network or positions not available');
        return false;
    }
}

// Attach drag end event handler to the vis.js network
function setupDragEndHandler() {
    if (window.visNetwork) {
        console.log('Adding dragEnd event listener to visNetwork');
        
        // Add the dragEnd event to track node position changes
        window.visNetwork.on('dragEnd', function(params) {
            if (params.nodes && params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const nodePosition = window.visNetwork.getPositions([nodeId])[nodeId];
                
                console.log('Node dragged:', nodeId, 'to position:', nodePosition);
                
                // Update stored positions
                if (!window.serverNodePositions) window.serverNodePositions = {};
                window.serverNodePositions[nodeId] = { 
                    x: nodePosition.x, 
                    y: nodePosition.y 
                };
                
                // Add more detailed logging
                console.log('Sending position update with payload:', {
                    id: nodeId,
                    x: nodePosition.x,
                    y: nodePosition.y
                });
                
                // Send position update to backend
                simpleSendMessage('pos', {
                    id: nodeId,
                    x: nodePosition.x,
                    y: nodePosition.y
                });
            }
        });
        
        console.log('dragEnd event handler attached successfully');
        return true;
    } else {
        console.error('visNetwork not available when trying to attach dragEnd handler');
        return false;
    }
}

// Initialize position setup
document.addEventListener('DOMContentLoaded', function() {
    // Try to set up the handler with retry logic
    var dragEndSetupAttempts = 0;
    var maxDragEndSetupAttempts = 20; // More attempts with longer total wait time
    
    function attemptDragEndSetup() {
        dragEndSetupAttempts++;
        console.log(`Attempt ${dragEndSetupAttempts}/${maxDragEndSetupAttempts} to set up dragEnd handler`);
        
        if (setupDragEndHandler()) {
            console.log('Successfully set up dragEnd handler');
        } else if (dragEndSetupAttempts < maxDragEndSetupAttempts) {
            // Try again after a delay, with increasing wait time
            var delay = 300 + (dragEndSetupAttempts * 100); // Gradually increase delay
            console.log(`Will retry in ${delay}ms...`);
            setTimeout(attemptDragEndSetup, delay);
        } else {
            console.error('Failed to set up dragEnd handler after maximum attempts');
        }
    }
    
    // Initial delay to give network time to initialize
    setTimeout(attemptDragEndSetup, 1000);
    
    // Also watch for the network object to become available
    var networkWatcher = setInterval(function() {
        if (window.visNetwork) {
            clearInterval(networkWatcher);
            console.log('Network detected by watcher, attempting to attach dragEnd handler');
            setupDragEndHandler();
        }
    }, 300);
    
    // Start automatic position tracking
    setInterval(function() {
        if (window.visNetwork) {
            for (const nodeId in window.positionDebug.trackNodes) {
                window.positionDebug.updateNodePosition(nodeId);
            }
        }
    }, 2000);
    
    // Enhance dragEnd handler to record position events
    if (window.visNetwork) {
        try {
            const origDragEnd = window.visNetwork.eventHandlers['dragEnd'];
            if (origDragEnd) {
                window.visNetwork.off('dragEnd');
                window.visNetwork.on('dragEnd', function(params) {
                    // Call original handler
                    origDragEnd(params);
                    
                    // Record for debugging
                    if (params.nodes && params.nodes.length > 0) {
                        const nodeId = params.nodes[0];
                        const positions = window.visNetwork.getPositions([nodeId]);
                        if (positions && positions[nodeId]) {
                            window.positionDebug.recordDragEvent(
                                nodeId, 
                                positions[nodeId].x, 
                                positions[nodeId].y
                            );
                        }
                    }
                });
                console.log('Enhanced dragEnd handler for position debugging');
            }
        } catch (e) {
            console.error('Error enhancing dragEnd handler:', e);
        }
    }
    
    // Also add mutation observer to detect when network is added to DOM
    var networkObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                for (var i = 0; i < mutation.addedNodes.length; i++) {
                    var node = mutation.addedNodes[i];
                    // Check if the added node is the network container or contains it
                    if (node.id === 'mynetwork' || (node.querySelector && node.querySelector('#mynetwork'))) {
                        console.log('Network container detected in DOM via MutationObserver');
                        // Check if we can access the network
                        setTimeout(function() {
                            // Try to detect network after the container is added
                            if (window.visNetwork) {
                                console.log('Network object available after container detection');
                                setupDragEndHandler();
                            } else {
                                // Try to find the network object in other ways
                                var networkDiv = document.getElementById('mynetwork');
                                if (networkDiv) {
                                    console.log('Found network div, looking for network object');
                                    var canvases = networkDiv.querySelectorAll('canvas');
                                    if (canvases.length > 0) {
                                        for (var j = 0; j < canvases.length; j++) {
                                            if (canvases[j].network) {
                                                console.log('Found network object in canvas');
                                                window.visNetwork = canvases[j].network;
                                                setupDragEndHandler();
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }, 500);
                    }
                }
            }
        });
    });
    
    // Start observing document body for changes
    networkObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
}); 