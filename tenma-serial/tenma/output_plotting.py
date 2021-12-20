import time
import serial

# Import plotting library
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from serial.serialutil import Timeout

# Import tenma library
from tenma.tenmaDcLib import instantiate_tenma_class_from_device_response, TenmaException
from tenma.tenmaDcLib import Tenma72_2535, Tenma72Base

from utils import enumerate_serial, autoselect_serial, getVersion


MAX_VOLTAGE = 3500
MAX_CURRENT = 60


class Tenma72_2535_manage:

    def __init__(self):
        # Seek for all connected device
        available_serial_port = enumerate_serial()
        # Select the port
        alim_serial_port = autoselect_serial(available_serial_port, ('VID:PID=0416:5011',))
        # Instantiate Tenma72_2535
        self.tenma72_2535 = Tenma72_2535(alim_serial_port, debug=True)
        print(self.tenma72_2535.getVersion())

    def power(self, state: str, verbose=False)-> str:
        if state == 'ON':
            self.tenma72_2535.ON()
        elif state == 'OFF':
            self.tenma72_2535.OFF()
        else:
            state = 'OFF'
            self.tenma72_2535.OFF()
            print('Command shall be ON or OFF.')
            print('Power set to OFF.')
        if verbose:
            print(f'For tenma72_2535: power is {state}.')
        return state

    def set_voltage(self, value: int=0, channel: int=1)-> int:
        '''Set the voltage value (in mV)'''
        if value > MAX_VOLTAGE:
            value = MAX_VOLTAGE
        self.tenma72_2535.setVoltage(channel, value)
        return value

    def set_current(self, value: int=0, channel: int=1)-> int:
        '''Set the current value (in mA)'''
        if value > MAX_CURRENT:
            value = MAX_CURRENT
        self.tenma72_2535.setCurrent(channel, value)
        return value

    # for port in ('COM1', 'COM2', 'COM3'):
# ser = serial.Serial(
#     'COM7',
#     # 19200,
#     115200,
#     timeout=3,
#     parity=serial.PARITY_ODD,
#     stopbits=serial.STOPBITS_ONE)
# ser.xonxoff = False
# ser.rtscts = False
# ser.dsrdtr = False
# ser.writeTimeout = 0.5
# ser.bytesize = serial.EIGHTBITS
# ser.setRTS(False) # required for tenma meters!

        # out = ser.readline() # make 

        # times,vals=[],[]
        # while True:
        #     times.append(time.time())
        #     vals.append(ser.readline().decode('ascii').strip())
        #     if len(times)<2:
        #         continue
        #     if abs(times[-1]-times[-2])>.1:
        #         if vals[-1]==vals[-1]:
        #             break
        #         else:
        #             print("values did not match! repeating measurement.")
        # print(vals[-1])
        
        
        
        # Read serial otput as a string
# out = ""
# count = 0
# while count < 1000:
#     count += 1
#     time.sleep(0.05)
#     in_waiting = ser.inWaiting()
#     if in_waiting > 0:
#         out += ser.read(1).decode('ascii')
# print("<< ", out)


# out += ser.read().decode('ascii')
# print("<< ", out)
# except Exception as inst:
#     print(f"Type:\t{type(inst)}")   # the exception instance
#     print(f"args:\t{inst.args}")    # arguments stored in .args
#     print(f"Except:\t{inst}")       # __str__ allows args to be printed directly,
#                                     # but may be overridden in exception subclasses
#     for i, x in enumerate(inst.args):   # unpack args
#         print('arg_', i, ' =', x)

# data = []
# tstamps = []
# timestamp = time.time()
# timestamp_mem = time.time()
# while timestamp - timestamp_mem < 3:
#     current = tenma72_2535.runningCurrent(1)
#     voltage = tenma72_2535.runningVoltage(1)
#     timestamp = time.time()

#     data.append(voltage)
#     tstamps.append(timestamp)

#     plt.clf()
#     plt.plot(tstamps, data)
#     plt.pause(0.5)

tenma72_2535.OFF()
tenma72_2535.close()
