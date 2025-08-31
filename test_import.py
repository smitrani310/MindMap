import sys
import os
sys.path.insert(0, os.getcwd())

print("Current working directory:", os.getcwd())
print("Python path:", sys.path[:3])

try:
    import src.infrastructure.ui_communication as ui_comm
    print("Module imported successfully")
    print("Module file:", ui_comm.__file__)
    print("Module attributes:", dir(ui_comm))
    
    if hasattr(ui_comm, 'CommunicationChannel'):
        print("CommunicationChannel found")
        print("CommunicationChannel type:", type(ui_comm.CommunicationChannel))
        if hasattr(ui_comm.CommunicationChannel, 'NODE_DATA'):
            print("NODE_DATA:", ui_comm.CommunicationChannel.NODE_DATA)
        else:
            print("NODE_DATA not found in CommunicationChannel")
    else:
        print("CommunicationChannel not found in module")
        
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()