// Ensure window object exists
if (typeof window !== 'undefined') {
    // Immediately define Streamlit namespace using IIFE to prevent syntax errors
    (function initStreamlit() {
        try {
            // Define Streamlit namespace if it doesn't exist
            if (typeof window.Streamlit === 'undefined') {
                window.Streamlit = { 
                    setComponentValue: function() { console.log('Streamlit mock: setComponentValue called'); },
                    setComponentReady: function() { console.log('Streamlit mock: setComponentReady called'); },
                    receiveMessageFromPython: function() { console.log('Streamlit mock: receiveMessageFromPython called'); }
                };
                console.log('Created Streamlit namespace mock to prevent errors');
            }
        } catch (e) {
            console.error('Error initializing Streamlit namespace:', e);
        }
    })();
}

// Utility functions for the Enhanced Mind Map

// Function to safely check if an object exists before accessing its properties
function safeGet(obj, path, defaultValue = null) {
    try {
        const parts = path.split('.');
        let current = obj;
        
        for (const part of parts) {
            if (current === null || current === undefined) {
                return defaultValue;
            }
            current = current[part];
        }
        
        return current !== undefined ? current : defaultValue;
    } catch (e) {
        console.error('Error in safeGet:', e);
        return defaultValue;
    }
}

// Function to safely call a function if it exists
function safeCall(func, ...args) {
    if (typeof func === 'function') {
        try {
            return func(...args);
        } catch (e) {
            console.error('Error calling function:', e);
            return null;
        }
    }
    return null;
}

// Export utilities
if (typeof window !== 'undefined') {
    window.MindMapUtils = {
        safeGet: safeGet,
        safeCall: safeCall
    };
} 