from .bms3_command import BMS3Command
from time import sleep
import sys

argv = sys.argv

bms3_command = BMS3Command()

if "-multimeter" in argv:
    for _ in range(30):
        sleep(2)
        print(bms3_command.get_measurement())
