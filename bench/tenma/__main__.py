from .tenma_dc_power import Tenma_72_2535_manage

tenma_dc_power = Tenma_72_2535_manage()
tenma_dc_power.set_voltage(3500)
tenma_dc_power.set_current(60)
tenma_dc_power.power('ON')
while(input('\n\n\tGet Tenma_72_2535 current (y/n)') in ' yY'):
    print(f'Output current = {tenma_dc_power.get_current()}')
tenma_dc_power.power('OFF')
