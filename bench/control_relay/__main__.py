import time

from .control_relay import ControlRelay

from ..utils.utils import RelayState


control_relay = ControlRelay(True)

for board in ('AC', 'AD'):
    for relay in range(1, 9):
        control_relay.manage_relay(board, relay, RelayState.Enable)
        time.sleep(0.3)
    for relay in range(1, 9):
        control_relay.manage_relay(board, relay, RelayState.Disable)
        time.sleep(0.1)
control_relay.disconnect()
