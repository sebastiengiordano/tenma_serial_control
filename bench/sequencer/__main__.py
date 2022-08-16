from .sequencer import Bms3Sequencer, Item
from time import sleep


bms3_sequencer = Bms3Sequencer(True)
bms3_sequencer.connect_tenma_alim()
bms3_sequencer._tenma_dc_set_voltage(3500, Item.BMS3)
bms3_sequencer._tenma_dc_power_on()
bms3_sequencer.press_push_in_button()
sleep(0.5)
bms3_sequencer.release_push_in_button()

bms3_sequencer.connect_debug_tx()
answer = input('\n\n\t\tStart test... press ENTER')
while(answer == ''):
    bms3_sequencer.connect_debug_rx()
    input('pause')
    bms3_sequencer.disconnect_debug_rx()
    answer = input('mesure = '
                   + f'{bms3_sequencer._bms3_interface.get_measurement()}'
                   + '\n\tContinuer ???')

bms3_sequencer._tenma_dc_power_on()
bms3_sequencer.disconnect_debug_tx()