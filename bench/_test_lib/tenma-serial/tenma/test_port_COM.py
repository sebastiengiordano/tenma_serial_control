import serial
import time
ports = ['COM3', 'COM4', 'COM1', 'COM2']
baud_rate = [50,75,110,134,150,200,1200,1800,2400,4800,9600,19200,38400,57600,115200]
parity = [serial.PARITY_ODD,serial.PARITY_EVEN,serial.PARITY_NONE]
stop_bits = [serial.STOPBITS_TWO, serial.STOPBITS_ONE]
bytesize = [serial.SEVENBITS,serial.EIGHTBITS]
# timeout = 5000
timeout = 1
start = time.time()
for port in ports:
    print(f'Test port {port}')
    for b in baud_rate:
        for p in parity:
            for s in stop_bits:
                for bs in bytesize:
                    ser = serial.Serial(port=port,baudrate=b,parity=p,stopbits=s,bytesize=bs, timeout=timeout)
                    try:
                        if ser.isOpen():
                            pass
                            # ser.write(b'TEST')
                            # ser.reset_output_buffer()
                            # time.sleep(1)
                            # out = ser.read_all().decode('ascii')
                            # if out[0] == 64 and out[1] == 67 and out[2] == 32:
                            #     print("dumping settings")
                            #     print(ser.get_settings())
                            # print(
                            #     f"baud_rate: {b}\n"
                            #     f"parity: {p}\n"
                            #     f"stop_bits: {s}\n"
                            #     f"bytesize: {bs}\n"
                            #     f"out: {out}\n"
                            # )
                        else:
                            ser.open()
                        out = ser.read_all().decode('ascii')
                        if not out == '':
                            print(
                                f"Name: {ser.name}\n"
                                f"port: {port}\n"
                                f"baud_rate: {b}\n"
                                f"parity: {p}\n"
                                f"stop_bits: {s}\n"
                                f"bytesize: {bs}\n"
                                f"out: {out}"
                            )
                        out = ser.read().decode('ascii')
                        if not out == '':
                            print(
                                f"Name: {ser.name}\n"
                                f"port: {port}\n"
                                f"baud_rate: {b}\n"
                                f"parity: {p}\n"
                                f"stop_bits: {s}\n"
                                f"bytesize: {bs}\n"
                                f"out: {out}"
                            )
                        else:
                            print(f'{(time.time() - start):.2f}', ' :', end='')
                            print(
                                f"Name: {ser.name}\t"
                                f"port: {port}\t"
                                f"baud_rate: {b}\t"
                                f"parity: {p}\t"
                                f"stop_bits: {s}\t"
                                f"bytesize: {bs}\t"
                                f"out: {out}")
                        ser.close()
                    except serial.SerialException as err:
                        print(f"Serial Exception occured: {err=}, {type(err)=}")
                        raise
                    except BaseException as err:
                        print(f"Unexpected {err=}, {type(err)=}")
                        raise