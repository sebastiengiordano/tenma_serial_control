import usb.core
import usb.util
import threading
from enum import Enum


class MeasurementFunction(Enum):
    Voltage = 1
    Current = 2
    Resistance = 3
    UnImplemented = 4


class OvfStatus(Enum):
    NoOverFlow = 0
    OverFlow = 1


class Tenma_72_7730A_manage(threading.Thread):

    def __init__(self, bcdDevice):
        threading.Thread.__init__(self)
        self.device = None
        self.configuration = None
        self.interface = None
        self.endpoint = None
        self.multimeter_data = []
        self.measurement = 0
        self.mode = None
        self.thread_run = True

        self._connect(bcdDevice)

    def _connect(self, bcdDevice):
        # Find our device
        self.device = usb.core.find(bcdDevice=bcdDevice)
        # Get configuration
        self.device.set_configuration()
        self.configuration = self.device.get_active_configuration()
        # Get interface
        self.interface = self.configuration[(0,0)]
        # Get endpoint
        self.endpoint = usb.util.find_descriptor(
            self.interface,
            custom_match = (
                lambda e:
                    usb.util.endpoint_direction(e.bEndpointAddress)
                    == usb.util.ENDPOINT_IN
                )
            )
        # Enable HID communication
        packet = [0x60, 0x09, 0, 0, 3]
        packet = packet + (64 - len(packet)) * [0]
        self.hid_set_report(packet)

    def run(self):
        while self.thread_run:
            waiting_for_packet = True
            self.multimeter_data = []
            try:
                while waiting_for_packet:
                    data = self.device.read(
                        self.endpoint.bEndpointAddress,
                        self.endpoint.wMaxPacketSize)
                    if list(data)[0] == 241:
                        self.multimeter_data.append(list(data)[1] & 0xF)
                    # Check if all data have been received
                    if (
                            len(self.multimeter_data) > 10
                            and self.multimeter_data[-2] == 13
                            and self.multimeter_data[-1] == 10):
                        if len(self.multimeter_data) > 11:
                            self.multimeter_data[-11:]
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
                    print(f'Error on device: {self.device}')
                    print(err)
                    print(err.__class__)
                    print(err.__doc__)
                    print(err.__dict__)
                    print()

    def kill(self):
        self.thread_run = False

    def get_measurement(self):
        return self.measurement

    def get_mode(self):
        return self.mode.name

    def _getDigits(self):
        dig = self.multimeter_data[0:5]
        s = ""
        if( max(dig) > 10 ):
            #overflow
            ovf = OvfStatus.OverFlow
        else:
            ovf = OvfStatus.NoOverFlow
            for i in dig:
                if( i < 10 ):
                    s += str(i)
        return s, ovf

    def _decodePacket(self):
        s, ovf = self._getDigits()
        r = self.multimeter_data[5:11]

        rangeVal = r[0]
        modeVal = r[1]

        decimal = 0
        mul = 1
        if modeVal == 1: #DC voltage
            self.mode = MeasurementFunction.Voltage
            decimal = rangeVal
        elif modeVal == 2: #mA
            self.mode = MeasurementFunction.Current
            decimal = rangeVal
        elif modeVal == 3: #mV
            self.mode = MeasurementFunction.Voltage
            decimal = 3
            mul = 1./1000
        elif modeVal == 4: #Ohm
            self.mode = MeasurementFunction.Resistance
            decimal = (rangeVal+1)%3 + 1
            mul = 1000**((rangeVal+1)//3)
        else:
            self.mode = MeasurementFunction.UnImplemented

        if ovf == OvfStatus.NoOverFlow:
            val = float(s[:decimal] + "." + s[decimal:])
        else:
            val = 0

        if r[3] & 0b100:
            val *= -1
        val *= mul

        self.measurement = val

    def hid_set_report(self, report):
        """ Implements HID SetReport via USB control transfer """

        self.device.ctrl_transfer(
            0x21,   # REQUEST_TYPE_CLASS | RECIPIENT_INTERFACE | ENDPOINT_OUT
            9,      # SET_REPORT
            (self.configuration.bDescriptorType
             * 0x100),                          # "Vendor" Descriptor Type + 0 Descriptor Index
            self.interface.bInterfaceNumber,    # USB interface
            report  # the HID payload as a byte array -- e.g. from struct.pack()
        )
