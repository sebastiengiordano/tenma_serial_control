
from time import sleep

from .control_relay import ControlRelay

from ..utils.utils import State


control_relay = ControlRelay(True)

while input(
        '\n\tPress ENTER to continu, '
        'or any key + ENTER to end test sequence\n') == '':
    for board in ('AD',):
    # for board in ('AB', 'AC', 'AD'):
        for relay in range(1, 9):
            control_relay.manage_relay(board, relay, State.Enable)
            sleep(0.3)
        for relay in range(1, 9):
            control_relay.manage_relay(board, relay, State.Disable)
            sleep(0.1)
control_relay.disconnect()
