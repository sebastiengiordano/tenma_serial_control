'''
This module aims to manage BMS3 firmware download and to read data
send by BMS3 in its DEBUG_TX output.
'''

from os.path import dirname, join as os_path_join, isfile
from os import listdir
from socket import timeout
import serial
import serial.tools.list_ports
from time import sleep
from threading import Thread

from .stm32loader import CommandInterface, CmdException

ADDRESS = 0x08000000
INVALID_VALUE = -1 * 0xFFFFFFFF


class BMS3Command:

    def __init__(self, verbose=False):
        self._command = CommandInterface()
        self._verbose = verbose
        self._voltage_measurement = INVALID_VALUE
        self._end_measurement = False
        self._connect_debug_tx_serial()
        self._set_firmware_folder()

    def kill(self) :
        self._end_measurement = True

    def get_measurement(self):
        # Waiting for reading last value
        sleep(.5)
        # 
        voltage_measurement = self._voltage_measurement
        self._voltage_measurement = INVALID_VALUE
        return voltage_measurement

    def _connect_to_serial(
            self,
            port: str,
            baudrate: int,
            bytesize = serial.EIGHTBITS,
            stopbits = serial.STOPBITS_ONE,
            parity = serial.PARITY_EVEN,
            timeout = 0.5
            ) -> serial.Serial:
        xonxoff = 0   # don't enable software flow control
        rtscts = 0    # don't enable RTS/CTS flow control

        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=bytesize,
            stopbits=stopbits,
            parity=parity,
            xonxoff=xonxoff,
            rtscts=rtscts)

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

    def _connect_debug_tx_serial(self):
        self._debug_tx_serial = self._connect_to_serial(
            port='COM8',
            baudrate=115200,
            parity=serial.PARITY_NONE,
            timeout=0.2
            )
        if not self._debug_tx_serial.is_open:
            self._debug_tx_serial.open()
        x = Thread(target=self._read_measurement)
        x.start()

    def _read_measurement(self):
        while not self._end_measurement:
            voltage_measurement = \
                self._debug_tx_serial.readline().decode(encoding='utf-8')
            if not voltage_measurement == '':
                self._voltage_measurement = int(voltage_measurement.strip())

    def _set_firmware_folder(self):
        module_dir = dirname(__file__)
        self._firmware_folder_path = os_path_join(
            module_dir,
            'bms3_firmwares')

    def _get_firmware_files_list(self) -> list[str]:
        firmware_files_list = self._files_in_folder(
            self._firmware_folder_path)
        return firmware_files_list

    def _files_in_folder(self, folder_path: str) -> list[str]:
        '''Return the list of all files in folder_path and its subfolder'''
        files_in_folder_path = []
        # Loop on all files or directories inside folder_path
        for file_or_dir in listdir(folder_path):
            file_or_dir_path = os_path_join(folder_path, file_or_dir)
            # If file_or_dir is a file
            if isfile(file_or_dir_path):
                # Add it to the files list
                files_in_folder_path.append(file_or_dir)
            else:
                # Loop inside the subfolder to find all files
                files_in_subfolder = self._files_in_folder(file_or_dir_path)
                # Add relative path from folder_path
                for index, file in enumerate(files_in_subfolder.copy()):
                    files_in_subfolder[index] = file_or_dir + "/" + file
                # Add this files to the files list
                files_in_folder_path += files_in_subfolder
        return files_in_folder_path

    def _connect_to_bms3(self):
        for port in self._port_list:
            try:
                ser = self._connect_to_serial(
                    port=port,
                    baudrate=115200
                    )
                self._command.set_serial(ser)
                self._command.cmdGetVersion()
                self._port_list.pop(port)
                return
            except:
                pass
        raise CmdException('Impossible de se connecter à la BMS3.')

    def _load_firmware(self, firmware_label: str) -> bool:
        # Check firmware avaibility
        firmware = firmware_label + '.bin'
        firmware_files_list = self._get_firmware_files_list
        if firmware not in firmware_files_list:
            raise CmdException(
                f'This {firmware_label} firmware is not '
                f'avaible in {self._firmware_folder_path}.')
        # Load firmware
        firmware_path = os_path_join(
            self._firmware_folder_path,
            firmware)
        data = map(lambda c: ord(c), open(firmware_path, 'rb').read())
        self._command.writeMemory(ADDRESS, data)
        # Check if the firmware is well loaded
        verify = self._command.readMemory(ADDRESS, len(data))
        self._command.releaseChip()
        if(data == verify):
            return True
        else:
            return False

    def _get_port_list(self) -> list[str]:
        # Seek for all connected device
        available_serial_port = serial.tools.list_ports.comports()
        port_list = []
        for port, desc, hwid in available_serial_port:
            port_list.append(port)
        return port_list

    def _get_debug_tx_serial(self):
        for port in self._port_list:
            try:
                ser = self._connect_to_serial(
                    port=port,
                    baudrate=115200
                    )
                line = ser.readline()
                line = line.decode(encoding='utf-8')
                if int(line) >= 0:
                    return ser
            except serial.SerialException:
                continue
        raise CmdException(
            'Impossible de lire sur les données du DEBUG_TX de la BMS3.')
