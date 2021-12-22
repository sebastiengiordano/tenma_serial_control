# Copyright (C) 2017 Jordi Castells
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
# @author Jordi Castells

"""
    Command line tenma control program for Tenma72_XXXX bank power supply
"""
import argparse

# TODO this is just a trick so tenmaControl runs cleanly from both the source tree
# and the pip installation
try:
    from tenma.tenmaDcLib import instantiate_tenma_class_from_device_response, TenmaException
except:
    from tenmaDcLib import instantiate_tenma_class_from_device_response, TenmaException


def main():
    parser = argparse.ArgumentParser(description='Control a Tenma 72-2540 power supply connected to a serial port')
    parser.add_argument('device', default="/dev/ttyUSB0")
    parser.add_argument('-v', '--voltage', help='set mV', required=False, type=int)
    parser.add_argument('-c', '--current', help='set mA', required=False, type=int)
    parser.add_argument('-C', '--channel', help='channel to set (if not provided, 1 will be used)', required=False, type=int, default=1)
    parser.add_argument('-s', '--save', help='Save current configuration to Memory', required=False, type=int)
    parser.add_argument('-r', '--recall', help='Load configuration from Memory', required=False, type=int)
    parser.add_argument('-S', '--status', help='Retrieve and print system status', required=False, action="store_true", default=False)
    parser.add_argument('--ocp-enable', dest="ocp", help='Enable overcurrent protection', required=False, action="store_true", default=None)
    parser.add_argument('--ocp-disable',dest="ocp", help='Disable overcurrent pritection', required=False, action="store_false", default=None)
    parser.add_argument('--ovp-enable', dest="ovp", help='Enable overvoltage protection', required=False, action="store_true", default=None)
    parser.add_argument('--ovp-disable',dest="ovp",  help='Disable overvoltage pritection', required=False, action="store_false", default=None)
    parser.add_argument('--beep-enable',dest="beep", help='Enable beeps from unit', required=False, action="store_true", default=None)
    parser.add_argument('--beep-disable',dest="beep", help='Disable beeps from unit', required=False, action="store_false", default=None)
    parser.add_argument('--on', help='Set output to ON', action="store_true", default=False)
    parser.add_argument('--off', help='Set output to OFF', action="store_true", default=False)
    parser.add_argument('--verbose', help='Chatty program', action="store_true", default=False)
    parser.add_argument('--debug', help='print serial commands', action="store_true", default=False)
    parser.add_argument('--script', help='runs from script. Only print result of query, no version', action="store_true", default=False)
    parser.add_argument('--runningCurrent', help='returns the running output current', action="store_true", default=False)
    parser.add_argument('--runningVoltage', help='returns the running output voltage', action="store_true", default=False)
    args = vars(parser.parse_args())

    T = None
    try:
        VERB = args["verbose"]
        T = instantiate_tenma_class_from_device_response(args["device"], args["debug"])
        if not args["script"]:
            print("VERSION: ", T.getVersion())

        # On saving, we want to move to the proper memory 1st, then
        # perform the current/voltage/options setting
        # and after that, perform the save
        if args["save"]:
            if VERB:
                print("Recalling Memory", args["save"])

            T.OFF() # Turn off for safety
            T.recallConf(args["save"])

        # Now, with memory, or no memory handling, perform the changes
        if args["ocp"] is not None:
            if VERB:
                if args["ocp"]:
                    print("Enable overcurrent protection")
                else:
                    print("Disable overcurrent protection")

            T.setOCP(args["ocp"])

        if args["ovp"] is not None:
            if VERB:
                if args["ovp"]:
                    print("Enable overvoltage protection")
                else:
                    print("Disable overvoltage protection")

            T.setOVP(args["ovp"])

        if args["beep"] is not None:
            if VERB:
                if args["beep"]:
                    print("Enable unit beep")
                else:
                    print("Disable unit beep")

            T.setBEEP(args["beep"])

        if args["voltage"]:
            if VERB:
                print("Setting voltage to ", args["voltage"])
            T.setVoltage(args["channel"], args["voltage"])

        if args["current"]:
            if VERB:
                print("Setting current to ", args["current"])
            T.setCurrent(args["channel"], args["current"])

        if args["save"]:
            if VERB:
                print("Saving to Memory", args["save"])

            T.saveConfFlow(args["save"], args["channel"])

        if args["recall"]:
            if VERB:
                print("Loading from Memory: ", args["recall"])

            T.recallConf(args["recall"])
            volt = T.readVoltage(args["channel"])
            curr = T.readCurrent(args["channel"])

            print("Loaded from Memory: ", args["recall"])
            print("Voltage:", volt)
            print("Current:", curr)

        if args["off"]:
            if VERB:
                print("Turning OUTPUT OFF")
            T.OFF()

        if args["on"]:
            if VERB:
                print("Turning OUTPUT ON")
            T.ON()

        if args["status"]:
            if VERB:
                print("Retrieving status")
            print(T.getStatus())

        if args["runningCurrent"]:
            if VERB:
                print("Retrieving running Current")
            print(T.runningCurrent(args["channel"]))

        if args["runningVoltage"]:
            if VERB:
                print("Retrieving running Voltage")
            print(T.runningVoltage(args["channel"]))

    except TenmaException as e:
        print("Lib ERROR: ", repr(e))
    finally:
        if VERB:
            print("Closing connection")
        if T:
            T.close()

if __name__ == "__main__":
    main()
