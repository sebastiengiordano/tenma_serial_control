from time import sleep

from .tenmaDcLib import Tenma72_2535

from ..utils.utils import enumerate_serial, autoselect_serial


MAX_VOLTAGE = 3500
MAX_CURRENT = 60
WAIT_AFTER_SETTING = 1.5


class Tenma_72_2535_manage:

    def __init__(self, vendor_product_id='VID:PID=0416:5011', debug=False):
        # Seek for all connected device
        available_serial_port = enumerate_serial()
        # Select the port
        alim_serial_port = autoselect_serial(
            available_serial_port,
            (vendor_product_id,))
        # Instantiate Tenma72_2535
        self.tenma72_2535 = Tenma72_2535(
            alim_serial_port,
            debug=debug)
        if self.tenma72_2535.ser.is_open:
            self._comm_port_status = 'Open'
        else:
            self._comm_port_status = 'Close'

    def power(self, state: str, verbose=False) -> str:
        if state == 'ON':
            self.tenma72_2535.ON()
        elif state == 'OFF':
            self.tenma72_2535.OFF()
        else:
            state = 'OFF'
            self.tenma72_2535.OFF()
            print('Command shall be ON or OFF.')
            print('Power set to OFF.')
        if verbose:
            print(f'For tenma72_2535: power is {state}.')
        self.state = state
        return state

    def set_voltage(self, value: int = 0, channel: int = 1) -> int:
        '''Set the voltage value (in mV)'''

        if value > MAX_VOLTAGE:
            value = MAX_VOLTAGE
        #  Value shall be a mulitple of 10mV
        value = value // 10 * 10
        self.tenma72_2535.setVoltage(channel, value)
        sleep(WAIT_AFTER_SETTING)
        return value

    def set_current(self, value: int = 0, channel: int = 1) -> int:
        '''Set the current value (in mA)'''

        if value > MAX_CURRENT:
            value = MAX_CURRENT
        self.tenma72_2535.setCurrent(channel, value)
        sleep(WAIT_AFTER_SETTING)
        return value

    def get_current(self, channel: int = 1) -> float:
        '''Get the current value (in mA)'''

        return self.tenma72_2535.readCurrent(channel)

    def disconnect(self):
        if self._comm_port_status == 'Open':
            self.power('OFF')
            self.tenma72_2535.close()
            self._comm_port_status = 'Close'

    def __del__(self):
        self.disconnect()
