'''
    · After the ICSE012A has been connected to PC,
    if send 0x50 to ICSE012A, it will reply 0xAB.
    ( Relay Board Manager: Tool--Configure)
    · Then if you send 0x51 to ICSE012A, it is ready to receive hex code.
    ( Relay Board Manager: Open the Sele)
Actually you can use a software “Bus Hound” to see what the transmission
hex codes are and use Python PySerial library to customize the relay actions
as well as “Relay Board Manager”.
'''

import serial
import time


baudrate = 9600

def connect_to_serial(port, baudrate, timeout, verbose=False):
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


def configure_relay_board(ser):
    ser.write(b'\x50')
    time.sleep(0.1)
    data, hexadecimal_string = read_port_com(ser, True)
    if hexadecimal_string in ('AB', 'AC', 'AD'):
        print('Relay Board Manager: Tool--Configure')
        ser.write(b'\x51')
        data = read_port_com(ser, True)
    else:
        print('Relay Board Manager: Tool--Not Configure')
        ser.write(b'\x51')
        data = read_port_com(ser, True)


def relay():
    command_list = [
        b'\x01',
        b'\x02',
        b'\x04',
        b'\x08',
        b'\x10',
        b'\x20',
        b'\x40',
        b'\x80',
        b'\xFF',
        b'\x00',
    ]
    for command in command_list:
        ser.write(command)
        print(f'\trelay command: {command}')
        time.sleep(1.5)


def read_port_com(ser, verbose=False):
    data = ser.readline()
    if verbose:
        print(f'data receieved:\t{data}\n'
              f'data to hex:\t{bytearray(data).hex()}')
    return data


for port in ('COM6', 'COM7'):
    ser = connect_to_serial(port, baudrate, 0.5, True)
    configure_relay_board(ser)
    relay()
