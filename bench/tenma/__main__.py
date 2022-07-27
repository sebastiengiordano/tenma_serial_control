import sys


argv = sys.argv

if "-dc_power" in argv:
    from .tenma_dc_power import Tenma_72_2535_manage
    tenma_dc_power = Tenma_72_2535_manage()
    tenma_dc_power.set_voltage(3500)
    tenma_dc_power.set_current(60)
    tenma_dc_power.power('ON')
    while(input('\n\n\tGet Tenma_72_2535 current (y/n)') in ' yY'):
        print(f'Output current = {tenma_dc_power.get_current()}')
    tenma_dc_power.power('OFF')


if "-multimeter" in argv:
    from .tenma_multimeter import Tenma_72_7730A_manage
    from time import sleep
    import usb.core
    from bench.sequencer.sequencer import ID_PRODUCT, ID_VENDOR
    
    
    def get_bcd_devices() -> list[int]:
        # Seek for all connected device
        devices = usb.core.find(find_all=True)
        # with open('usb_devices', 'w') as f:
        #     for d in devices:
        #         f.write(d._str())
        #         f.write('\n')
        # Select all Tenma_72_2535
        bcdDevices = []
        for device in devices:
            if (
                    device.idProduct == ID_PRODUCT
                    and
                    device.idVendor == ID_VENDOR
                    and
                    device.bcdDevice not in bcdDevices):
                bcdDevices.append(device.bcdDevice)
        return bcdDevices

    
    # Intialization
    ampmeter = None
    voltmeter = None
    well_connected = True
    frame = '*' * 56
    frame = '\n\t' + frame
    # Seek for Voltmeter and Ampmeter
    bcdDevices = get_bcd_devices()
    for bcdDevice in bcdDevices:
        tenma_multimeter = Tenma_72_7730A_manage(bcdDevice)
        tenma_multimeter.start()
        sleep(1)
        if tenma_multimeter.get_mode() == 'Current':
            ampmeter = tenma_multimeter
        elif tenma_multimeter.get_mode() == 'Voltage':
            voltmeter = tenma_multimeter
    for _ in range(10):
        print()
        print(f'\tampmeter : {ampmeter.get_measurement()}')
        print(f'\tvoltmeter : {voltmeter.get_measurement()}')
        sleep(.4)
