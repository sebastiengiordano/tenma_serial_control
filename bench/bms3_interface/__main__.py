from .bms3_command import BMS3Command
from time import sleep

bms3_command = BMS3Command()

for _ in range(30):
    sleep(2)
    print(bms3_command.get_measurement())
