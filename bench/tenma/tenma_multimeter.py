'''
tenma_multimeter.py - a python script to access data from
TENMA multimeters 72_7730A through their supplied IR cable via USB port.
The Tenma_72_7730A_manage class provides the following king of measurement:
    Voltage in Volt
    Current in mA
    Resistance in Ohm

In order to known which kind of measurement the multimeter send,
used the get_mode() method which send a string corresponding to
the kind of measurement.

In order to known the last value measured by the multimeter,
used the get_measurement() method.

When you end your treatment, in order to close propely the application,
used the kill() method.
'''

import usb.core
import usb.util
import threading
from enum import Enum


class MeasurementFunction(Enum):
    Voltage = 1
    Current = 8
    Resistance = 4
    UnImplemented = -1


class OvfStatus(Enum):
    NoOverFlow = 0
    OverFlow = 1


class Tenma_72_7730A_manage(threading.Thread):

    def __init__(self, bcdDevice):
        threading.Thread.__init__(self, daemon=True)
        self._device = None
        self._configuration = None
        self._interface = None
        self._endpoint = None
        self._multimeter_data = []
        self._measurement = 0
        self._mode = None
        self._thread_run = True

        try:
            self._connect(bcdDevice)
        except NotImplementedError:
            print(
                '\n\t'
                '************************************************************'
                '\n\t\t'
                'Veuillez débrancher puis rebrancher les multimètres.'
                '\n\t'
                '************************************************************')

    def _connect(self, bcdDevice):
        # Find our device
        self._device = usb.core.find(bcdDevice=bcdDevice)
        # Get configuration
        self._device.set_configuration()
        self._configuration = self._device.get_active_configuration()
        # Get interface
        self._interface = self._configuration[(0, 0)]
        # Get endpoint
        self._endpoint = usb.util.find_descriptor(
            self._interface,
            custom_match=(
                lambda e:
                    usb.util.endpoint_direction(e.bEndpointAddress)
                    == usb.util.ENDPOINT_IN
                )
            )
        # Enable HID communication
        packet = [0x60, 0x09, 0, 0, 3]
        packet = packet + (64 - len(packet)) * [0]
        self._hid_set_report(packet)

    def run(self):
        while self._thread_run:
            waiting_for_packet = True
            self._multimeter_data = []
            try:
                while waiting_for_packet:
                    data = self._device.read(
                        self._endpoint.bEndpointAddress,
                        self._endpoint.wMaxPacketSize)
                    if list(data)[0] == 241:
                        self._multimeter_data.append(list(data)[1] & 0xF)
                    # Check if all data have been received
                    if (
                            len(self._multimeter_data) > 10
                            and self._multimeter_data[-2] == 13
                            and self._multimeter_data[-1] == 10):
                        if len(self._multimeter_data) > 11:
                            self._multimeter_data[-11:]
                        waiting_for_packet = False
                self._decodePacket()
            except Exception as err:
                if (
                        err.backend_error_code == -7
                        or err.backend_error_code == -116):
                    # Normal, the read was empty
                    pass
                else:
                    print()
                    print(f'Error on device: {self._device}')
                    print(err)
                    print(err.__class__)
                    print(err.__doc__)
                    print(err.__dict__)
                    print()

    def get_measurement(self) -> int:
        return self._measurement

    def get_mode(self) -> str:
        if self._mode is None:
            return ''
        else:
            return self._mode.name

    def _getDigits(self):
        dig = self._multimeter_data[0:5]
        s = ""
        if(max(dig) > 10):
            # Overflow
            ovf = OvfStatus.OverFlow
        else:
            ovf = OvfStatus.NoOverFlow
            for i in dig:
                if(i < 10):
                    s += str(i)
        return s, ovf

    def _decodePacket(self):
        s, ovf = self._getDigits()
        r = self._multimeter_data[5:11]

        rangeVal = r[0]
        modeVal = r[1]

        decimal = 0
        mul = 1
        # Voltage (V)
        if modeVal == MeasurementFunction.Voltage.value:
            self._mode = MeasurementFunction.Voltage
            decimal = rangeVal
        # Current (mA)
        elif modeVal == MeasurementFunction.Current.value:
            self._mode = MeasurementFunction.Current
            decimal = (rangeVal + 1) % 3 + 1
            mul = 1000**((rangeVal + 1) // 3)
        # Resistance (Ohm)
        elif modeVal == MeasurementFunction.Resistance.value:
            self._mode = MeasurementFunction.Resistance
            decimal = (rangeVal + 1) % 3 + 1
            mul = 1000**((rangeVal + 1) // 3)
        else:
            self._mode = MeasurementFunction.UnImplemented

        if ovf == OvfStatus.NoOverFlow:
            val = float(s[:decimal] + "." + s[decimal:])
        else:
            val = 0

        if r[3] & 0b100:
            val *= -1
        val *= mul

        self._measurement = val

    def _hid_set_report(self, report):
        """ Implements HID SetReport via USB control transfer """

        self._device.ctrl_transfer(
            # REQUEST_TYPE_CLASS | RECIPIENT_INTERFACE | ENDPOINT_OUT
            0x21,
            # SET_REPORT
            9,
            # "Vendor" Descriptor Type + 0 Descriptor Index
            (self._configuration.bDescriptorType
             * 0x100),
            # USB interface
            self._interface.bInterfaceNumber,
            # the HID payload as a byte array -- e.g. from struct.pack()
            report
        )
