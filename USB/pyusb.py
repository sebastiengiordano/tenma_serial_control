import usb.core
import usb.util
import time

# List USB device in Terminal
# device = usb.core.show_devices(True)

# find our device
dev = usb.core.find(bcdDevice=0x1400)
# dev = usb.core.find(idVendor=0x1a86, idProduct=0xe0082)
# dev = usb.core.find(idVendor=0x1022, idProduct=0x15e0)
# dev = usb.core.find(idVendor=0x1022, idProduct=0x15e1)
# dev = usb.core.find(idVendor=0x0416, idProduct=0x5011)
# dev = usb.core.find(idVendor=0x1022, idProduct=0x43bc)
# dev = usb.core.find()
# was it found?
if dev is None:
    raise ValueError('Device not found')

# for cfg in dev:
#     print(cfg)
#     print(cfg.bEndpointAddress)
# cfg = dev[1]

# set the active configuration. With no arguments, the first
# configuration will be the active one
# dev.set_configuration()

# alt = usb.util.find_descriptor(dev, find_all=True)

endpoint = dev[0][(0,0)][0]

start = time.time()
for _ in range(256):
    data = dev.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize, 100)
    print (time.time() - start, ' :\t', data)

# get an endpoint instance
cfg = dev.get_active_configuration()
intf = cfg[(0,0)]

ep = usb.util.find_descriptor(
    intf,
    # match the first OUT endpoint
    custom_match = \
    lambda e: \
        usb.util.endpoint_direction(e.bEndpointAddress) == \
        usb.util.ENDPOINT_OUT)

assert ep is not None

# write the data
ep.write('test')
