import serial.tools.list_ports
import time


# Lists serial ports courtesy of Thomas from stack overflow
def enumerate_serial():
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
