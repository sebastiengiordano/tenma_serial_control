from enum import Enum

from .tenma.temna_dc_power import Tenma72_2535_manage


class MeasurementFunction(Enum):
    Voltage = 1
    Current = 2
    Resistance = 3
    UnImplemented = 4


class OvfStatus(Enum):
    NoOverFlow = 0
    OverFlow = 1


def getDigits(data):
    dig = data[0:5]
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


def decodePacket(data):
    
    s, ovf = getDigits(data)
    r = data[5:11]
    print ("rest:", [hex(i) for i in r])

    rangeVal = r[0]
    modeVal = r[1]

    decimal = 0
    mul = 1
    if modeVal == 1: #DC voltage
        mode = MeasurementFunction.Voltage
        decimal = rangeVal
    elif modeVal == 3: #mV
        mode = MeasurementFunction.Voltage
        decimal = 3
        mul = 1./1000
    elif modeVal == 4: #Ohm
        mode = MeasurementFunction.Resistance
        decimal = (rangeVal+1)%3 + 1
        mul = 1000**((rangeVal+1)//3)
    else:
        mode = MeasurementFunction.UnImplemented

    if ovf == OvfStatus.NoOverFlow:
        val = float(s[:decimal] + "." + s[decimal:])
    else:
        val = 0

    if r[3] & 0b100:
        val *= -1
    val *= mul

    value = val

    print ()
    print (value)
    print (mode)
    print (ovf)
    return (value)


def hid_set_report(dev, conf, intf, report):
      """ Implements HID SetReport via USB control transfer """
    #   dev.ctrl_transfer(
    #       0x21,  # REQUEST_TYPE_CLASS | RECIPIENT_INTERFACE | ENDPOINT_OUT
    #       9,     # SET_REPORT
    #       0x200, # "Vendor" Descriptor Type + 0 Descriptor Index
    #       0,     # USB interface № 0
    #       report # the HID payload as a byte array -- e.g. from struct.pack()
    #   )
      dev.ctrl_transfer(
          0x21,  # REQUEST_TYPE_CLASS | RECIPIENT_INTERFACE | ENDPOINT_OUT
          9,     # SET_REPORT
          conf.bDescriptorType * 0x100, # "Vendor" Descriptor Type + 0 Descriptor Index
          intf.bInterfaceNumber,     # USB interface
          report # the HID payload as a byte array -- e.g. from struct.pack()
      )


if __name__ == "__main__":
    import time
    import usb.core
    import usb.util

    dc_power = Tenma72_2535_manage()
    dc_power.set_voltage(1234)
    dc_power.set_current(60)
    dc_power.power('ON')


    # List USB device in Terminal
    device = usb.core.show_devices()
    devices = list(usb.core.find(find_all=True))

    # find our device
    dev = usb.core.find(bcdDevice=0x1400)
    dev.set_configuration()
    cfg = dev.get_active_configuration()
    intf = cfg[(0,0)]
    endpoint = usb.util.find_descriptor(
        intf,
        custom_match = (
            lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress)
                == usb.util.ENDPOINT_IN
            )
        )
    dev.reset()
    usb.util.dispose_resources(dev)
    # usb.util.claim_interface(dev, 0)
    # endpoint = dev[0][(0, 0)][0]
for _ in range(20):
    multimeter_data = []
    raw_multimeter_data = []
    waiting_for_packet = True
    try:
        while waiting_for_packet:
            data = dev.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize)
            if list(data)[0] == 241:
                multimeter_data.append(list(data)[1] & 0xF)
                raw_multimeter_data.append(list(data)[1])
            # All data has been received
            if len(multimeter_data) > 10 and multimeter_data[-2] == 13 and multimeter_data[-1] == 10:
                if len(multimeter_data) > 11:
                    multimeter_data[-11:]
                waiting_for_packet = False
        print('multimeter_data :\t', multimeter_data)
        decodePacket(multimeter_data)
    except Exception as err:
        if err.backend_error_code == -7 or err.backend_error_code == -116:
            # Normal, the read was empty
            print(err)
            pass
        else:
            print()
            print(f'Error on device: {dev}')
            print(err)
            print(err.__class__)
            print(err.__doc__)
            print(err.__dict__)
            print()

dc_power.power('OFF')
dc_power.disconnect()