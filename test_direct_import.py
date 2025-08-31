import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

print("Testing direct import...")

try:
    # Try importing the module directly
    import importlib.util
    spec = importlib.util.spec_from_file_location("ui_communication", "src/infrastructure/ui_communication.py")
    ui_comm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ui_comm)
    
    print("Module loaded successfully")
    print("Available attributes:", [attr for attr in dir(ui_comm) if not attr.startswith('_')])
    
    if hasattr(ui_comm, 'CommunicationChannel'):
        print("CommunicationChannel found!")
        print("NODE_DATA:", ui_comm.CommunicationChannel.NODE_DATA)
    else:
        print("CommunicationChannel not found")
        
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()