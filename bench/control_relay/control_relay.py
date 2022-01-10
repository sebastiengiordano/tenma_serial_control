'''
This module aims to drive control relay board through serial port.

Those serial port are emulated with chip driver
which could be recognized thank to its VID/PID.
Then, with the hardware ID of each serial port,
the control boards are identified.
'''

import serial
from time import sleep

from ..utils.utils import (
    enumerate_serial, get_all_serial_with_hwid,
    State)


class ControlRelay:
    baudrate = 9600

    def __init__(self, verbose=False):
        # Set debug flag
        self._verbose = verbose
        # Initialize connection to control relay board
        self._initialize_connection()
        # Check connection
        self._check_connection()
        # Configure relay board
        self._configure_relay_board(self._control_relay_ac)
        self._configure_relay_board(self._control_relay_ad)

    def manage_relay(self, board: str, relay: int, state: State):
        if relay not in range(1, 9):
            raise ValueError('Relay could only be in range 1 to 8.')
        if board not in ['AC', 'AD']:
            raise ValueError('Only control relay board AC or AD are managed.')
        if board == 'AC':
            # Update the command value of board AC
            self._command_ac = self._update_command(
                self._command_ac,
                relay,
                state)
            # Send command to board AC
            self._send_command(
                self._control_relay_ac,
                self._command_ac
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
        if self._verbose:
            print(
                f'Board \'{board}\': '
                f'Relay n°{relay} {state.name}')

    def disconnect(self):
        self._send_command(
            self._control_relay_ac,
            0xFF)
        self._send_command(
            self._control_relay_ad,
            0xFF)
        self._control_relay_ac.close()
        self._control_relay_ad.close()
        if self._verbose:
            print(
                f'Port {self._control_relay_ac.port} closed.'
                '\n'
                f'Port {self._control_relay_ad.port} closed.')

    def _initialize_connection(self):
        # Get port and id
        port_and_id = self._get_port_and_id()
        # Set serial device
        self._control_relay_ac = None
        self._control_relay_ad = None
        for port, id in port_and_id:
            if id == 'AC':
                self._control_relay_ac = self._connect_to_serial(
                    port=port,
                    baudrate=self.baudrate)
                self._command_ac = 0xFF
            elif id == 'AD':
                self._control_relay_ad = self._connect_to_serial(
                    port=port,
                    baudrate=self.baudrate)
                self._command_ad = 0xFF

    def _check_connection(self):
        fail_connection_list = []
        if self._control_relay_ac is None:
            fail_connection_list.append('AC')
        if self._control_relay_ad is None:
            fail_connection_list.append('AD')
        if len(fail_connection_list) > 0:
            if len(fail_connection_list) == 1:
                sentence = (
                    'Failed to connect to control relay board '
                    f'{fail_connection_list[0]}.')
            else:
                sentence = (
                    'Failed to connect to control relay board AC adn AD.')
            raise RuntimeError(sentence)

    def _connect_to_serial(
            self,
            port: str,
            baudrate: int,
            timeout: int = 1
            ) -> serial.Serial:
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
        if self._verbose:
            border = "-" * 34 + "\n"
            print(
                "\n",
                border,
                'Connection'.center(len(border)),
                "\n",
                border,
                f"\tport:\t\t{port}\n"
                f"\tbaud_rate:\t{baudrate}\n",
                f"\ttimeout:\t{timeout}\n",
                f"\tbytesize:\t{bytesize}\n",
                f"\tstopbits:\t{stopbits}\n",
                f"\tparity:\t{parity}\n",
                border)
        sleep(0.5)
        return ser

    def _configure_relay_board(self, ser: serial.Serial):
        '''Start communication with relay board.'''
        ser.write(b'\x50')
        sleep(0.1)
        ser.write(b'\x51')
        sleep(0.1)
        ser.write(b'\xFF')
        if self._verbose:
            print(f'Configure relay board on {ser.port}.')

    def _get_port_and_id(self) -> list(tuple(str)):
        # Seek for all connected device
        available_serial_port = enumerate_serial()
        # Select the port
        port_list = get_all_serial_with_hwid(
            available_serial_port,
            ('VID:PID=0403:6011',))
        port_and_id = []
        for port, desc, hwid in available_serial_port:
            if port in port_list:
                port_and_id.append((port, hwid[-2:].upper()))
        return port_and_id

    def _send_command(self, ser: serial.Serial, value: int):
        command = self._format_command(value)
        ser.write(command)

    def _format_command(self, value: int) -> bytearray:
        return bytearray([value])

    def _update_command(
            self,
            current_command: int,
            relay: int,
            state: State):
        if state == State.Enable:
            update_command = current_command - 2**(relay - 1)
        else:
            update_command = current_command + 2**(relay - 1)
        return update_command

    def _read_port_com(self, ser: serial.Serial, verbose=False) -> str:
        data = ser.readline()
        if verbose:
            print(
                f'data received:\t{data}\n'
                f'data to hex:\t{bytearray(data).hex()}')
        return data
