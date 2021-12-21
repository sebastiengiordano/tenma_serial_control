from .tenma.temna_dc_power import Tenma_72_2535_manage
from .tenma.tenma_multimeter import MeasurementFunction, Tenma_72_7730A_manage

if __name__ == "__main__":
    import time
    import usb.core
    import usb.util

    dc_power = Tenma_72_2535_manage()
    multimeter = Tenma_72_7730A_manage(0x1400)
    multimeter.start()

    dc_power.set_current(60)
    dc_power.power('ON')

    delta = []

    try:
        for time_after_set_voltage in range(1000, 3101, 200):
            # init
            dc_power.set_voltage(2800)
            time.sleep(.5)
            for voltage in range(2800, 3601, 200):
                dc_power.set_voltage(voltage)
                time.sleep(time_after_set_voltage / 1000)
                measurement = int(multimeter.get_measurement() * 1000)
                delta.append(voltage - measurement)
            print(
                f'{time_after_set_voltage}\n'
                f'{(sum(delta)/len(delta)):.1f}\n'
                f'{min(delta)}\n'
                f'{max(delta)}\n'
                f'{delta}\n'
                )
    except Exception as err:
                    print()
                    print(err)
                    print(err.__class__)
                    print(err.__doc__)
                    print(err.__dict__)
                    print()
        
    dc_power.power('OFF')
    dc_power.disconnect()
    multimeter.kill()
    print('\tTest end.')
