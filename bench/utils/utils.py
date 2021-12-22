import serial.tools.list_ports
from enum import Enum


def enumerate_serial():
    # Lists serial ports courtesy of Thomas from stack overflow
    return (serial.tools.list_ports.comports())


def autoselect_serial(available_serial_port, patterns=("STM", "STLink")):
    if available_serial_port is not None:
        for port, desc, hwid in available_serial_port:
            pattern_position = 0
            pattern_position_mem = -1
            for pattern in patterns:
                pattern_position = hwid.find(pattern, pattern_position)
                if not pattern_position < 0 and pattern_position != pattern_position_mem:
                    pattern_position_mem = pattern_position
                    return port
                else:
                    selected_serial = None
                    break

    return selected_serial


def get_all_serial_with_hwid(available_serial_port, patterns=("STM", "STLink")):
    all_serial_with_hwid = []
    if available_serial_port is not None:
        for port, desc, hwid in available_serial_port:
            pattern_position = 0
            pattern_position_mem = -1
            for pattern in patterns:
                pattern_position = hwid.find(pattern, pattern_position)
                if not pattern_position < 0 and pattern_position != pattern_position_mem:
                    pattern_position_mem = pattern_position
                    selected_serial = port
                else:
                    selected_serial = None
                    break
            if selected_serial is not None:
                all_serial_with_hwid.append(selected_serial)
    return all_serial_with_hwid


class RelayState(Enum):
    Enable = 'Enable'
    Disable = 'Disable'
