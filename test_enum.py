from enum import Enum

class TestChannel(Enum):
    NODE_DATA = "node_data"
    UI_STATE = "ui_state"

print(TestChannel.NODE_DATA)
print(TestChannel.NODE_DATA.value)