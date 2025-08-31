from enum import Enum

class CommunicationChannel(Enum):
    """Communication channels for UI messages."""
    NODE_DATA = "node_data"
    UI_STATE = "ui_state"
    SYSTEM_STATUS = "system_status"
    NOTIFICATIONS = "notifications"
    EVENTS = "events"
    USER_ACTIONS = "user_actions"

print(f"CommunicationChannel type: {type(CommunicationChannel)}")
print(f"NODE_DATA: {CommunicationChannel.NODE_DATA}")
print(f"NODE_DATA value: {CommunicationChannel.NODE_DATA.value}")