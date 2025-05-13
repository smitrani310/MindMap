#!/usr/bin/env python
"""
MindMap Runner with Position Fix

This script runs the MindMap application with the position fixes applied.
"""

import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('position_fix_run.log')
    ]
)
logger = logging.getLogger('mindmap_runner')

def run_app():
    """Run the MindMap application"""
    logger.info("Starting MindMap application with position fixes")
    
    # Check if Streamlit is installed
    try:
        import streamlit
        logger.info("Streamlit is installed")
    except ImportError:
        logger.error("Streamlit is not installed. Please install it with: pip install streamlit")
        return False
    
    # Check if the main.py file exists
    if not os.path.exists('main.py'):
        logger.error("main.py not found! Make sure you're running this from the MindMap directory")
        return False
    
    # Run the application with Streamlit
    try:
        logger.info("Launching MindMap with Streamlit")
        subprocess.run(["streamlit", "run", "main.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running MindMap: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("MindMap stopped by user")
        return True

if __name__ == "__main__":
    try:
        # Notify about position fix
        print("=" * 60)
        print("MindMap with Position Fix")
        print("=" * 60)
        print("This version includes fixes for node position persistence.")
        print("Nodes should now maintain their positions across sessions.")
        print()
        print("To verify that positions are working correctly:")
        print("1. Drag nodes to new positions")
        print("2. Refresh the page")
        print("3. Verify that nodes remain where you placed them")
        print()
        print("If you encounter any issues, please check the logs in:")
        print("- position_fix_run.log")
        print("- logs/ directory")
        print("=" * 60)
        
        # Run the app
        success = run_app()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        sys.exit(1) 