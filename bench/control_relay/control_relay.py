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
        self._configure_relay_board(self._control_relay_a)
        self._configure_relay_board(self._control_relay_b)
        self._configure_relay_board(self._control_relay_c)
        self._configure_relay_board(self._control_relay_d)

    def manage_relay(self, board: str, relay: int, state: State):
        if relay not in range(1, 9):
            raise ValueError('Relay could only be in range 1 to 8.')
        if board not in ['A', 'B', 'C', 'D']:
            raise ValueError(
                'Only control relay board A, B, C or D are managed.')
        if board == 'A':
            # Update the command value of board A
            self._command_a = self._update_command(
                self._command_a,
                relay,
                state)
            # Send command to board A
            self._send_command(
                self._control_relay_a,
                self._command_a
            )
        elif board == 'B':
            # Update the command value of board B
            self._command_b = self._update_command(
                self._command_b,
                relay,
                state)
            # Send command to board B
            self._send_command(
                self._control_relay_b,
                self._command_b
            )
        elif board == 'C':
            # Update the command value of board C
            self._command_c = self._update_command(
                self._command_c,
                relay,
                state)
            # Send command to board C
            self._send_command(
                self._control_relay_c,
                self._command_c
            )
        elif board == 'D':
            # Update the command value of board D
            self._command_d = self._update_command(
                self._command_d,
                relay,
                state)
            # Send command to board D
            self._send_command(
                self._control_relay_d,
                self._command_d
            )
        # Wait for treatment
        sleep(0.1)
        # Verbosity purpose
        if self._verbose:
            print(
                f'Board \'{board}\': '
                f'Relay n°{relay} {state.name}')

    def __del__(self):
        # Disconnect relays board A
        self._disconnect_relays_board(self._control_relay_a)
        # Disconnect relays board B
        self._disconnect_relays_board(self._control_relay_b)
        # Disconnect relays board C
        self._disconnect_relays_board(self._control_relay_c)
        # Disconnect relays board D
        self._disconnect_relays_board(self._control_relay_d)
        if self._verbose:
            print(
                f'Port {self._control_relay_a.port} closed.'
                '\n'
                f'Port {self._control_relay_b.port} closed.'
                '\n'
                f'Port {self._control_relay_c.port} closed.'
                '\n'
                f'Port {self._control_relay_d.port} closed.')

    def _initialize_connection(self):
        # Get port and id
        port_and_id = self._get_port_and_id()
        # Set serial device
        self._control_relay_a = None
        self._control_relay_b = None
        self._control_relay_c = None
        self._control_relay_d = None
        for port, id in port_and_id:
            if id == 'A':
                self._control_relay_a = self._connect_to_serial(
                    port=port,
                    baudrate=self.baudrate)
                self._command_a = 0xFF
            elif id == 'B':
                self._control_relay_b = self._connect_to_serial(
                    port=port,
                    baudrate=self.baudrate)
                self._command_b = 0xFF
            elif id == 'C':
                self._control_relay_c = self._connect_to_serial(
                    port=port,
                    baudrate=self.baudrate)
                self._command_c = 0xFF
            elif id == 'D':
                self._control_relay_d = self._connect_to_serial(
                    port=port,
                    baudrate=self.baudrate)
                self._command_d = 0xFF

    def _check_connection(self):
        fail_connection_list = []
        if self._control_relay_a is None:
            fail_connection_list.append('A')
        if self._control_relay_b is None:
            fail_connection_list.append('B')
        if self._control_relay_c is None:
            fail_connection_list.append('C')
        if self._control_relay_d is None:
            fail_connection_list.append('D')
        if len(fail_connection_list) > 0:
            if len(fail_connection_list) == 1:
                sentence = (
                    'Failed to connect to control relay board '
                    f'{fail_connection_list[0]}.')
            elif len(fail_connection_list) == 2:
                sentence = (
                    'Failed to connect to control relay board '
                    f'{fail_connection_list[0]} '
                    f'and {fail_connection_list[1]}.')
            elif len(fail_connection_list) == 3:
                sentence = (
                    'Failed to connect to control relay board '
                    f'{fail_connection_list[0]}, '
                    f'{fail_connection_list[1]} '
                    f'and {fail_connection_list[2]}.')
            else:
                sentence = (
                    'Failed to connect to control relay board A, B, C and D.')
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

    def _get_port_and_id(self) -> list[tuple[str]]:
        # Seek for all connected device
        available_serial_port = enumerate_serial()
        # Select the port
        port_list = get_all_serial_with_hwid(
            available_serial_port,
            ('VID:PID=0403:6011',))
        port_and_id = []
        for port, desc, hwid in available_serial_port:
            if port in port_list:
                port_and_id.append((port, hwid[-1:].upper()))
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
            # Corresponding bit shall be set to 0
            update_command = current_command & (0xff - (1 << (relay - 1)))
        else:
            # Corresponding bit shall be set to 1
            update_command = current_command | (1 << relay - 1)
        return update_command

    def _read_port_com(self, ser: serial.Serial, verbose=False) -> str:
        data = ser.readline()
        if verbose:
            print(
                f'data received:\t{data}\n'
                f'data to hex:\t{bytearray(data).hex()}')
        return data

    def _disconnect_relays_board(self, ser: serial.Serial):
        if (ser is not None and ser.is_open):
            self._send_command(ser, 0xFF)
            ser.close()
