from os.path import dirname, join as os_path_join, isfile
from os import listdir
import serial
import serial.tools.list_ports
from time import sleep

from .stm32loader import CommandInterface, CmdException

ADDRESS = 0x08000000


class BMS3Command:

    def __init__(self, verbose=False):
        self._command = CommandInterface()
        self._verbose = verbose
        self._set_firmware_folder()
        self._port_list = self._get_port_list()
        self._debug_tx_serial_port = None

    def connect_to_bms3(self):
        for port in self._port_list:
            try:
                ser = self._connect_to_serial(
                    port=port,
                    baudrate=115200
                    )
                self._command.set_serial(ser)
                self._command.cmdGetVersion()
                self._port_list.pop(port)
            finally:
                pass
        raise CmdException('Impossible de se connecter à la BMS3.')

    def load_firmware(self, firmware_label: str) -> bool:
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

    def read_debug_tx(self) -> str:
        if self._debug_tx_serial is None:
            self._debug_tx_serial = self._get_debug_tx_serial()
        self._debug_tx_serial.readline()
        return self._debug_tx_serial.readline().decode(encoding='utf-8')

    def _connect_to_serial(
            self,
            port: str,
            baudrate: int
            ) -> serial.Serial:
        timeout = 5
        bytesize = serial.EIGHTBITS
        stopbits = serial.STOPBITS_ONE
        parity = serial.PARITY_EVEN
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

    def _get_port_list(self) -> list(str):
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
            finally:
                pass
        raise CmdException(
            'Impossible de lire sur les données du DEBUG_TX de la BMS3.')

    def _set_firmware_folder(self):
        module_dir = dirname(__file__)
        self._firmware_folder_path = os_path_join(
            module_dir,
            'bms3_firmwares')

    def _get_firmware_files_list(self) -> list(str):
        firmware_files_list = self._files_in_folder(
            self._firmware_folder_path)
        return firmware_files_list

    def _files_in_folder(self, folder_path: str) -> list(str):
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
