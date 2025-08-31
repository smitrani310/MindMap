import sys
sys.path.insert(0, '.')

try:
    from src.infrastructure.ui_communication import CommunicationChannel
    print("Import successful")
    print(f"CommunicationChannel type: {type(CommunicationChannel)}")
    print(f"CommunicationChannel dir: {dir(CommunicationChannel)}")
    if hasattr(CommunicationChannel, 'NODE_DATA'):
        print(f"NODE_DATA: {CommunicationChannel.NODE_DATA}")
    else:
        print("NODE_DATA not found")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()