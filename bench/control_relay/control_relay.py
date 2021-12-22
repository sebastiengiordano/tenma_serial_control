import serial
import time

from ..utils.utils import (
    enumerate_serial, get_all_serial_with_hwid,
    RelayState)

class ControlRelay:
    baudrate = 9600
    
    def __init__(self):
        # Initialize connection to control relay board
        self._initialize_connection()
        # Check connection
        self._check_connection()

    def manage_relay(self, board: str, relay: int, state: RelayState):
        if relay not in range(1, 9):
            raise ValueError('Relay could only be in range 1 to 8.')
        if board not in ['AB', 'AD']:
            raise ValueError('Only control relay board AB or AD are managed.')
        if board == 'AB':
            # Update the command value of board AB
            self._command_ab = self._update_command(
                self._command_ab,
                relay,
                state)
            # Send command to board AB
            self._send_command(
                self._control_relay_ab,
                self._command_ab
            )
        if board == 'AD':
            # Update the command value of board AD
            self._command_ad = self._update_command(
                self._command_ad,
                relay,
                state)
            # Send command to board AD
            self._send_command(
                self._control_relay_ad,
                self._command_ad
            )

    def _initialize_connection(self):
        # Get port and id
        port_and_id = self._get_port_and_id()
        # Set serial device
        self._control_relay_ab = None
        self._control_relay_ad = None
        for port, id in port_and_id:
            if id == 'AB':
                self._control_relay_ab = self._connect_to_serial(
                    port=port,
                    baudrate=self.baudrate)
                self._command_ab = 0xFF
            elif id == 'AD':
                self._control_relay_ad = self._connect_to_serial(
                    port=port,
                    baudrate=self.baudrate)
                self._command_ad = 0xFF

    def _check_connection(self):
        fail_connection_list = []
        if self._control_relay_ab is None:
            fail_connection_list.append('AB')
        if self._control_relay_ad is None:
            fail_connection_list.append('AD')
        if fail_connection_list is not []:
            if len(fail_connection_list) == 1:
                sentence = f'Failed to connect to control relay board {fail_connection_list[0]}.'
            else:
                sentence = f'Failed to connect to control relay board AB adn AD.'
            raise RuntimeError(sentence)

    def _connect_to_serial(
            self,
            port,
            baudrate,
            timeout=1,
            verbose=False
            )-> serial.Serial:
        bytesize = serial.EIGHTBITS
        stopbits = serial.STOPBITS_ONE
        parity = serial.PARITY_NONE
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=bytesize,
            stopbits=stopbits,
            parity=parity)
        if verbose:
            border = "-" * 34 + "\n"
            print(
                "\n",
                border,
                f"\tport:\t\t{port}\n"
                f"\tbaud_rate:\t{baudrate}\n",
                f"\ttimeout:\t{timeout}\n",
                f"\tbytesize:\t{bytesize}\n",
                f"\tstopbits:\t{stopbits}\n",
                f"\tparity:\t{parity}\n",
                border)
        time.sleep(0.5)
        return ser

    def _configure_relay_board(self, ser: serial.Serial):
        '''Start communication with relay board.'''
        ser.write(b'\x50')
        time.sleep(0.1)
        ser.write(b'\x51')
        time.sleep(0.1)

    def _get_port_and_id(self):
        # Seek for all connected device
        available_serial_port = enumerate_serial()
        # Select the port
        port_list = get_all_serial_with_hwid(available_serial_port, ('VID:PID=0403:6011',))
        port_and_id = []
        for port, desc, hwid in available_serial_port:
            if port in port_list:
                port_and_id.append((port, hwid[-2:].upper()))
        return port_and_id

    def _send_command(self, ser: serial.Serial, value):
        command = self._format_command(value)
        ser.write(command)

    def _format_command(self, value):
        return bytearray([value])

    def _update_command(
            self,
            current_command: int,
            relay: int,
            state: RelayState):
        if state == RelayState.Enable:
            update_command = current_command - 2**(relay - 1)
        else:
            update_command = current_command + 2**(relay - 1)
        return update_command

    def _read_port_com(self, ser: serial.Serial, verbose=False):
        data = ser.readline()
        if verbose:
            print(f'data received:\t{data}\n'
                f'data to hex:\t{bytearray(data).hex()}')
        return data


if __name__ == "__main__":
    pass
