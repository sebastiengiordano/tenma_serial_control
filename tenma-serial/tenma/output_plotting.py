import time
import serial

# Import plotting library
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Import tenma library
from tenma.tenmaDcLib import instantiate_tenma_class_from_device_response, TenmaException
from tenma.tenmaDcLib import Tenma72_2535, Tenma72Base

from utils import enumerate_serial, autoselect_serial, getVersion

# Seek for all connected device
available_serial_port = enumerate_serial()
# Select the port
alim_serial_port = autoselect_serial(available_serial_port, ('VID:PID=0416:5011',))
# Instantiate Tenma72_2535
tenma72_2535 = Tenma72_2535(alim_serial_port, debug=True)
print(tenma72_2535.getVersion())


tenma72_2535.setVoltage(1, 3000)
tenma72_2535.setCurrent(1, 60)

try:
    ser = serial.Serial(
        'COM3',
        19200,
        timeout=0,
        parity=serial.PARITY_EVEN, rtscts=1)
except:
    pass

data = []
tstamps = []
timestamp = time.time()
timestamp_mem = time.time()
while timestamp - timestamp_mem < 10:
    current = tenma72_2535.runningCurrent(1)
    voltage = tenma72_2535.runningVoltage(1)
    timestamp = time.time()

    data.append(voltage)
    tstamps.append(timestamp)

    plt.clf()
    plt.plot(tstamps, data)
    plt.pause(0.5)

tenma72_2535.close()
