#!/usr/bin/env python3
"""
Simple test script to check canvas interactions by examining console logs.

This script will:
1. Start the app
2. Provide instructions for testing canvas interactions
3. Show what to look for in browser console
"""

import subprocess
import sys
import time
import webbrowser

def main():
    print("🧪 Canvas Interaction Test")
    print("=" * 50)
    
    print("\n📋 Test Instructions:")
    print("1. The app will start automatically")
    print("2. Open browser developer tools (F12)")
    print("3. Go to the Console tab")
    print("4. Try these interactions on the canvas:")
    print("   - Single click on a node")
    print("   - Double click on a node") 
    print("   - Right click on a node")
    print("   - Click on empty space")
    
    print("\n🔍 What to look for in console:")
    print("✅ SUCCESS indicators:")
    print("   - '🚀 Loading canvas interaction JavaScript...'")
    print("   - '✅ Canvas interaction JavaScript loaded'")
    print("   - 'POSTMESSAGE: Sending message to parent: canvas_click'")
    print("   - 'Canvas clicked at (x, y) on canvas WxH'")
    print("   - 'Selected node X: NodeName'")
    
    print("\n❌ ERROR indicators:")
    print("   - 'ERROR: mynetwork div not found'")
    print("   - 'POSTMESSAGE: Communication failed'")
    print("   - 'No node found near click position'")
    print("   - Any JavaScript errors in red")
    
    print("\n🐛 Debug commands you can run in console:")
    print("   - window.visNetwork (should show network object)")
    print("   - window.serverNodePositions (should show node positions)")
    print("   - window.positionDebug.getDebugInfo() (position tracking)")
    print("   - window.directParentCommunication.sendMessage('test', {}) (test messaging)")
    
    print("\n🚀 Starting app...")
    
    try:
        # Start the app
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "main_new.py",
            "--server.headless", "false",
            "--server.port", "8508"
        ])
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Try to open browser
        try:
            webbrowser.open("http://localhost:8508")
            print("✅ Browser should open automatically")
        except:
            print("⚠️  Please open http://localhost:8508 manually")
        
        print("\n⏳ App is running. Press Ctrl+C to stop when done testing.")
        
        # Wait for user to stop
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping app...")
        process.terminate()
        process.wait()
        print("✅ App stopped")
    except Exception as e:
        print(f"❌ Error starting app: {e}")

if __name__ == "__main__":
    main()