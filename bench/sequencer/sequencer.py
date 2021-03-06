from subprocess import CompletedProcess, TimeoutExpired
import usb.core
from time import sleep
from sys import exit
from os import system
from os.path import join as os_path_join, normpath

from bench.control_relay.control_relay import ControlRelay
from bench.tenma.tenma_dc_power import Tenma_72_2535_manage
from bench.tenma.tenma_multimeter import Tenma_72_7730A_manage
from bench.logger.logger import Logger
from bench.bms3_interface.bms3_command import BMS3Command, INVALID_VALUE

from bench.utils.utils import State, ConnectionState
from bench.utils.menus import Menu, menu_frame_design

# Test parameters
VOLTAGE_MEASUREMENT_TOLERANCE = 5                       # %
V_OUT_TOLERANCE = 100                                   # mV
V_OUT_TEST_CURRENT_TOLERANCE = 5                        # %
V_OUT_TEST_RESISTOR_WHEN_NO_LOAD = 100000               # Ohm
V_OUT_TEST_RESISTOR_WHEN_LOW_LOAD_FOR_9_V = 470         # Ohm
V_OUT_TEST_RESISTOR_WHEN_LOW_LOAD_FOR_18_V = 1500       # Ohm
V_OUT_TEST_RESISTOR_WHEN_HIGH_LOAD = 100000             # Ohm
CURRENT_CONSOMPTION_SLEEP_MODE_LOW_THRESHOLD = 0.001    # mA
CURRENT_CONSOMPTION_SLEEP_MODE_HIGH_THRESHOLD = 0.01    # mA
BATTERY_CHARGE_CURRENT_HIGH_THRESHOLD = 270             # mA
BATTERY_CHARGE_CURRENT_LOW_THRESHOLD = 230              # mA

# Logging
LOGGING_FOLDER = "../../logging"
DEFAULT_LOG_LABEL = 'BMS3_post_prod_test'
LOG_COLUMNS_WIDTH = [5, 35, 10, 75]

# Multimeter
ID_PRODUCT = 0xE008
ID_VENDOR = 0x1A86

ILLEGAL_NTFS_CHARS = "[<>:/\\|?*\"]|[\0-\31]"


class Bms3Sequencer():

    ########################
    # Class Initialization #
    ########################
    def __init__(self):
        # Set bench control device
        self._control_relay = ControlRelay()
        self._tenma_dc_power = Tenma_72_2535_manage()
        # Set measurement tools
        self._set_multimeter()
        # Set logger
        self._set_logger()
        # Set HAL
        self._set_hal()
        # Set BMS3 interface
        self._bms3_interface = BMS3Command()
        self._set_firmware_label()
        # Set other variables
        self._test_in_progress = True
        self._test_count = 0
        self._test_voltage = ''
        self._lot_number = ''
        # Run tests
        self.run()

    ##################
    # Public methods #
    ##################
    def run(self):
        while self._test_in_progress:
            self._test_sequence()
        exit()

    # DC power
    def connect_tenma_alim(self):
        if self._tenma_alim_state == ConnectionState.Disconnected:
            self._tenma_alim_state == ConnectionState.Connected
            self.disconnect_isolated_alim()
            self._activate_relay(self._relay_tenma_alim)

    def disconnect_tenma_alim(self):
        if self._tenma_alim_state == ConnectionState.Connected:
            self._tenma_alim_state == ConnectionState.Disconnected
            self._desactivate_relay(self._relay_tenma_alim)

    def connect_isolated_alim(self):
        if self._isolated_alim_state == ConnectionState.Disconnected:
            self._isolated_alim_state == ConnectionState.Connected
            self.disconnect_tenma_alim()
            self._activate_relay(self._relay_isolated_alim)

    def disconnect_isolated_alim(self):
        if self._isolated_alim_state == ConnectionState.Connected:
            self._isolated_alim_state == ConnectionState.Disconnected
            self._desactivate_relay(self._relay_isolated_alim)

    # BMS3 input management
    def press_push_in_button(self):
        self._activate_relay(self._relay_push_in)

    def release_push_in_button(self):
        self._desactivate_relay(self._relay_push_in)

    def bms3_wake_up(self):
        self.connect_tenma_alim()
        self._tenma_dc_power_on()
        self._tenma_dc_set_voltage(3500)
        self.press_push_in_button()
        sleep(0.5)
        self.release_push_in_button()

    def activate_jmp_18_v(self):
        self._activate_relay(self._relay_jmp_18_v)

    def desactivate_jmp_18_v(self):
        self._desactivate_relay(self._relay_jmp_18_v)

    def connect_debug_tx(self):
        self._activate_relay(self._relay_debug_tx)
        self._activate_relay(self._relay_gnd)

    def disconnect_debug_tx(self):
        self._desactivate_relay(self._relay_debug_tx)
        self._desactivate_relay(self._relay_gnd)

    def connect_debug_rx(self):
        self._activate_relay(self._relay_debug_rx)

    def disconnect_debug_rx(self):
        self._desactivate_relay(self._relay_debug_rx)

    def connect_reprog(self):
        self._activate_relay(self._relay_swclk)
        self._activate_relay(self._relay_nrst)
        self._activate_relay(self._relay_swdio)
        self._activate_relay(self._relay_2V5)
        self._activate_relay(self._relay_gnd)

    def disconnect_reprog(self):
        self._desactivate_relay(self._relay_swclk)
        self._desactivate_relay(self._relay_nrst)
        self._desactivate_relay(self._relay_swdio)
        self._desactivate_relay(self._relay_2V5)
        self._desactivate_relay(self._relay_gnd)

    # Connect/disconnected Vout
    def connect_low_load(self):
        self._desactivate_relay(self._relay_high_load)
        if self._test_voltage == '9':
            self._activate_relay(self._relay_low_load_9_V)
        else:
            self._activate_relay(self._relay_low_load_18_V)
        sleep(.5)

    def connect_high_load(self):
        self._desactivate_relay(self._relay_low_load_9_V)
        self._desactivate_relay(self._relay_low_load_18_V)
        self._activate_relay(self._relay_high_load)
        sleep(.5)

    def disconnect_load(self):
        self._desactivate_relay(self._relay_low_load_9_V)
        self._desactivate_relay(self._relay_low_load_18_V)
        self._desactivate_relay(self._relay_high_load)

    # Connect/disconnected measurement tools
    def activate_current_measurement(self):
        self._activate_relay(self._relay_current_measurement_in)
        self._activate_relay(self._relay_current_measurement_out)

    def desactivate_current_measurement(self):
        self._desactivate_relay(self._relay_current_measurement_in)
        self._desactivate_relay(self._relay_current_measurement_out)

    def activate_bms3_battery_measurement(self):
        self.desactivate_v_out_measurement()
        self._activate_relay(self._relay_bms3_battery_measurement_minus)
        self._activate_relay(self._relay_bms3_battery_measurement_plus)

    def desactivate_bms3_battery_measurement(self):
        self._desactivate_relay(self._relay_bms3_battery_measurement_minus)
        self._desactivate_relay(self._relay_bms3_battery_measurement_plus)

    def activate_v_out_measurement(self):
        self.desactivate_bms3_battery_measurement()
        self._activate_relay(self._relay_v_out_measurement_minus)
        self._activate_relay(self._relay_v_out_measurement_plus)

    def desactivate_v_out_measurement(self):
        self._desactivate_relay(self._relay_v_out_measurement_minus)
        self._desactivate_relay(self._relay_v_out_measurement_plus)

    # Connect/disconnected USB (Vcc/ Ground)
    def connect_usb_power(self):
        self._activate_relay(self._relay_usb_vcc)
        self._activate_relay(self._relay_usb_ground)

    def disconnect_usb_power(self):
        self._desactivate_relay(self._relay_usb_vcc)
        self._desactivate_relay(self._relay_usb_ground)

    # Disable all relays
    def disable_all_relays(self):
        for relay in self._relay_list:
            if relay['state'] == State.Enable:
                self._desactivate_relay(relay)

    ###################
    # Private methods #
    ###################

                #######################
                #   Test procedures   #
                #######################
    def _test_sequence(self):
        try:
            # Ask for board number
            self._ask_for_board_number()
            board_number = self._test_report['Board number']

            # BMS3 load firmware if requested
            if self._load_firmware_enable:
                process_return, std_out = self._load_firmware(self._firmware_label)
                if not isinstance(process_return, CompletedProcess):
                    self._manage_reprog_trouble(process_return, std_out)
                    raise Exception(std_out)

            # BMS3 wake up
            self.bms3_wake_up()

            # Test: Battery voltage measurement
            self._battery_voltage_measurement_test()

            # Test: Vout test
            self._v_out_test()

            # Test: Current consomption in sleep mode
            self._current_consomption_in_sleep_mode_test()

            # Test: Battery charge
            self._battery_charge_test()

            # Test: LED colors
            self._led_colors_test()

        except Exception as err:
            self._add_exception_to_log(err)

            # Display error
            print('\n\t'
                  'L\'erreur suivante est survenu :'
                  '\n\t\t'
                  f'{err}'
                  '\n\t'
                  f'Lors du test de la carte {board_number}.')

            # Stop logging
            self._logger.stop_logging(
                f'BMS3 - {self._test_count} tests.')
            input('\n\t\t'
                  'Test termin??.'
                  '\n\n\t'
                  '(Appuyer sur la touche ENTER)')
            exit()

        finally:
            # Display test result
            print('\n\t'
                  f'Resultat du test de la carte {board_number} => '
                  f'{self._test_status()}')

            # Update log file
            self._update_log()

            # Disable all relay
            self.disable_all_relays()

        ####################################
        # Battery voltage measurement test #
        ####################################
    def _battery_voltage_measurement_test(self):
        # Init test
        test_report_status = []
        voltage_to_check = [
            3500,
            3150,
            2800]
        self.activate_bms3_battery_measurement()

        # BMS3 battery voltage measurement tests
        for voltage in voltage_to_check:
            self._tenma_dc_set_voltage(voltage)
            test_report_status.append(
                self._battery_voltage_measurement_check())

        # Evaluate test reports status
        if False not in test_report_status:
            self._test_report[
                'Battery voltage measurement'][
                    'status'] = 'Test OK'

    def _battery_voltage_measurement_check(self) -> bool:
        # Get measurements
        voltage_measurement = self._voltmeter.get_measurement() * 1000
        bms3_voltage_measurement = self._get_bms3_voltage_measurement()

        # Set voltage threshold
        threshold = voltage_measurement * VOLTAGE_MEASUREMENT_TOLERANCE / 100
        measurement_high_threshold = voltage_measurement + threshold
        measurement_low_threshold = voltage_measurement - threshold

        # Add measurement values to test report
        self._test_report['Battery voltage measurement']['values'].append(
            str(bms3_voltage_measurement)
            + ' / '
            + str(voltage_measurement))

        # Check measurement values
        if (
                bms3_voltage_measurement < measurement_high_threshold
                and
                bms3_voltage_measurement > measurement_low_threshold):
            return True
        else:
            return False

        #############
        # Vout test #
        #############
    def _v_out_test(self):
        # Init test
        test_report_status = []
        self.activate_current_measurement()
        self.activate_v_out_measurement()
        # Set voltage to check and current threshold
        (voltage_to_check,
        low_load_current_low_threshold,
        low_load_current_high_threshold,
        high_load_current_low_threshold,
        high_load_current_high_threshold) = self._v_out_test_set_value_to_check()

        # Test low load
        self.connect_low_load()
        test_report_status.append(
            self._v_out_test_check(
                voltage_to_check,
                low_load_current_low_threshold,
                low_load_current_high_threshold))

        # Disconnect load and wait for BMS3 detection (300 ms in source code)
        self.disconnect_load()
        sleep(.5)

        # Test high load
        self.connect_high_load()
        test_report_status.append(
            self._v_out_test_check(
                voltage_to_check,
                high_load_current_low_threshold,
                high_load_current_high_threshold))

        # Disconnect load and wait for BMS3 detection (300 ms in source code)
        self.disconnect_load()
        sleep(.5)

        # Test no load
        test_report_status = self._v_out_test_no_load(test_report_status)

        # Evaluate test reports status
        self._v_out_evaluate_test(test_report_status)

        # End Vout test
        self.disconnect_load()
        # Wait for BMS3 detection (300 ms in source code)
        sleep(.5)

    def _v_out_test_set_value_to_check(self) -> tuple[int]:
        if self._test_voltage == '9':
            # Set voltage_to_check and current threshold for Vout = 9 V
            voltage_to_check = 9000
            low_load_current = (voltage_to_check
                       / V_OUT_TEST_RESISTOR_WHEN_LOW_LOAD_FOR_9_V)
            high_load_current = (voltage_to_check
                       / V_OUT_TEST_RESISTOR_WHEN_HIGH_LOAD)
        else:
            # Set voltage_to_check and current threshold for Vout = 18 V
            voltage_to_check = 18000
            low_load_current = (voltage_to_check
                       / V_OUT_TEST_RESISTOR_WHEN_LOW_LOAD_FOR_18_V)
            high_load_current = (voltage_to_check
                       / V_OUT_TEST_RESISTOR_WHEN_HIGH_LOAD)
        return (
            voltage_to_check,
            int(low_load_current * (100 - V_OUT_TEST_CURRENT_TOLERANCE) / 100),
            int(low_load_current * (100 + V_OUT_TEST_CURRENT_TOLERANCE) / 100),
            int(high_load_current * (100 - V_OUT_TEST_CURRENT_TOLERANCE) / 100),
            int(high_load_current * (100 + V_OUT_TEST_CURRENT_TOLERANCE) / 100))

    def _v_out_test_no_load(self, test_report_status: list) -> list:
        # Get battery voltage in order to check that
        # its the same voltage as Vout
        self.activate_bms3_battery_measurement()
        sleep(.5)
        battery_voltage_measurement = self._voltmeter.get_measurement()
        self.activate_v_out_measurement()
        sleep(.5)
        # Set current threshold
        current_low_threshold = int(
            battery_voltage_measurement
            / V_OUT_TEST_RESISTOR_WHEN_NO_LOAD
            * (100 - V_OUT_TEST_CURRENT_TOLERANCE) / 100)
        current_high_threshold = int(
            battery_voltage_measurement
            / V_OUT_TEST_RESISTOR_WHEN_NO_LOAD
            * (100 + V_OUT_TEST_CURRENT_TOLERANCE) / 100)
        test_report_status.append(
            self._v_out_test_check(
                battery_voltage_measurement,
                current_low_threshold,
                current_high_threshold))
        return test_report_status

    def _v_out_test_check(
            self,
            voltage_to_check: int,
            current_low_threshold: int,
            current_high_threshold: int) -> list:
        # Get measurements
        v_out_measurement = self._voltmeter.get_measurement()
        current_measurement = self._ampmeter.get_measurement()

        # Set voltage threshold
        voltage_high_threshold = voltage_to_check + V_OUT_TOLERANCE
        voltage_low_threshold = voltage_to_check - V_OUT_TOLERANCE

        # Add measurement values to test report
        self._test_report['Vout test']['voltage values'].append(
            str(v_out_measurement)
            + ' / '
            + str(voltage_to_check))
        self._test_report['Vout test']['current values'].append(
            str(current_measurement)
            + ' / '
            + str(current_low_threshold)
            + ' / '
            + str(current_high_threshold))

        # Check measurement values
        if (
                (
                    v_out_measurement < voltage_high_threshold
                    and
                    v_out_measurement > voltage_low_threshold)
                and
                (
                    current_measurement < current_high_threshold
                    and
                    current_measurement > current_low_threshold
                )):
            return True
        else:
            return False

    def _v_out_evaluate_test(self, test_report_status: list):
        # Evaluate test reports status
        if False not in test_report_status:
            self._test_report[
                'Vout test'][
                    'status'] = 'Test OK'

        ##########################################
        # Current consomption in sleep mode test #
        ##########################################
    def _current_consomption_in_sleep_mode_test(self):
        # Init test
        self.activate_current_measurement()
        sleep(.5)
        # Get measurement
        current_measurement = self._ampmeter.get_measurement()

        # Add measurement values to test report
        self._test_report['Current consomption in sleep mode']['value'] = (
            str(current_measurement)
            + ' / '
            + str(CURRENT_CONSOMPTION_SLEEP_MODE_LOW_THRESHOLD)
            + ' / '
            + str(CURRENT_CONSOMPTION_SLEEP_MODE_HIGH_THRESHOLD))

        # Check measurement values
        if (
                current_measurement < CURRENT_CONSOMPTION_SLEEP_MODE_HIGH_THRESHOLD
                and
                current_measurement > CURRENT_CONSOMPTION_SLEEP_MODE_LOW_THRESHOLD):
            self._test_report[
                'Current consomption in sleep mode'][
                    'status'] = 'Test OK'

        #######################
        # Battery charge test #
        #######################
    def _battery_charge_test(self):
        # Init test
        self.connect_isolated_alim()
        self.connect_usb_power()
        sleep(0.5)

        # Get measurement
        current_measurement = self._ampmeter.get_measurement()
        self._test_report[
                'Battery charge'][
                    'value'] = current_measurement

        # Check measurement values
        if (
                current_measurement < BATTERY_CHARGE_CURRENT_HIGH_THRESHOLD
                and
                current_measurement > BATTERY_CHARGE_CURRENT_LOW_THRESHOLD):
            self._test_report[
                'Battery charge'][
                    'status'] = 'Test OK'

        ###################
        # LED colors test #
        ###################
    def _led_colors_test(self):
        sentence = '\tTest de la couleur des LED.'
        frame = '*' * (16 + len(sentence))
        frame = '\n' + frame + '\n'
        print(
            frame,
            sentence,
            frame)
        # Test the blue LED
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED bleue est allum??e '
            'et sa couleur conforme ? (y/n)\t',
            'status_blue')
        # Test the green LED
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED verte est allum??e '
            'et sa couleur conforme ? (y/n)\t',
            'status_green')
        # Test the red LED
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED rouge est allum??e '
            'et sa couleur conforme ? (y/n)\t',
            'status_red')
        # Evaluate test reports status
        if 'Test NOK' not in (
                self._test_report['LED colors']['status_red'],
                self._test_report['LED colors']['status_green'],
                self._test_report['LED colors']['status_blue']):
            self._test_report[
                'LED colors'][
                    'status'] = 'Test OK'

    def _led_colors_check(
            self,
            question,
            test_in_progress):
        # Wait for user
        sleep(0.5)
        # Activate the LED
        self._activate_led()
        # Ask for LED check
        answer = input(question)
        # Desactivate the LED
        self._desactivate_led()
        # Evaluate answer
        if answer in 'yY':
            # Test OK
            self._test_report['LED colors'][test_in_progress] = 'Test OK'
        elif answer not in 'nN':
            # Wrong answer, shall be in 'yYnN'
            print('\t\t*********************************')
            print('\t\t* Wrong answer, shall be y or n *')
            print('\t\t*       Test will restart       *')
            print('\t\t*********************************')
            # Toogle led until the good one
            self._desactivate_led()
            sleep(.1)
            self._activate_led()
            sleep(2)
            self._desactivate_led()
            sleep(.1)
            self._activate_led()
            sleep(2)
            self._desactivate_led()
            self._led_colors_check(
                question,
                test_in_progress)

    def _activate_led(self):
        self.activate_jmp_18_v()

    def _desactivate_led(self):
        self.desactivate_jmp_18_v()

    # Logging
    def _set_logger(self) -> None:
        logging_name = self._set_logging_name()
        self._logger = Logger(
            logging_name=logging_name,
            logging_folder=normpath(os_path_join(LOGGING_FOLDER + self._lot_number)),
            columns_width=LOG_COLUMNS_WIDTH)
        self._test_report = self._init_test_report()

    def _set_logging_name(self) -> str:
        logging_name= ILLEGAL_NTFS_CHARS
        while(True in [caracter in ILLEGAL_NTFS_CHARS for caracter in logging_name]):
            logging_name = input(
                '\n\t'
                'Entrer le nom de la s??rie de test.'
                '\n\n\t'
                'Rmq: ou taper sur ENTER pour utiliser'
                '\n\t'
                f'le nom par d??faut: {DEFAULT_LOG_LABEL}.'
                '\n'
            )
        if logging_name == '':
            logging_name = DEFAULT_LOG_LABEL

        logging_name = self._set_9_18_voltage(logging_name)
        logging_name = self._set_lot_number(logging_name)

        return logging_name

    def _set_9_18_voltage(self, logging_name: str) -> str:
        while(self._test_voltage not in ['9', '18']):
            self._test_voltage = input(
                '\n\t'
                'Entrer le type de test (9 / 18 V)'
                '\n\t\t'
                '1: 18 V'
                '\n\t\t'
                '9: 9 V'
                '\n'
            )
            if self._test_voltage == '1':
                self._test_voltage = '18'

        return logging_name + '_' + self._test_voltage + 'V'

    def _set_lot_number(self, logging_name: str) -> str:
        while(self._lot_number == '' or (True in [caracter in ILLEGAL_NTFS_CHARS for caracter in self._lot_number])):
            self._lot_number = input(
                '\n\t'
                'Entrer le num??ro de lot :'
                '\n\t\t'
            )
         

        return logging_name + '_' + self._lot_number

    def _init_test_report(self) -> dict:
        return {
            'Board number': 'Not Defined',
            'Battery voltage measurement': (
                {'status': 'Test NOK',
                 'values': []}),
            'Vout test': (
                {'status': 'Test NOK',
                 'voltage values': [],
                 'current values': []}),
            'Current consomption in sleep mode': (
                {'status': 'Test NOK',
                 'value': -1}),
            'Battery charge': (
                {'status': 'Test NOK',
                 'value': -1}),
            'LED colors': {
                'status': 'Test NOK',
                'status_red': 'Test NOK',
                'status_green': 'Test NOK',
                'status_blue': 'Test NOK'}
        }

    def _update_log(self):
        self._logger.add_lines_to_logging_file([''])
        # Board number
        self._logger.add_lines_to_logging_file([
            '', 'Board number',
            self._test_report['Board number'],
            self._test_status()])

        # Battery voltage measurement
        # Add status to log file
        self._logger.add_lines_to_logging_file([
            '', 'Battery voltage measurement',
            self._test_report['Battery voltage measurement']['status'],
            'BMS3 measurement / Voltmeter measurement'])
        # Get measurement values
        values = self._test_report['Battery voltage measurement']['values']
        # Add measurement values to log file
        for value in values:
            self._logger.add_lines_to_logging_file([
                '', '', '',
                value])

        # Vout test
        # Add status to log file
        self._logger.add_lines_to_logging_file([
            '', 'Vout test',
            self._test_report['Vout test']['status']])
        # Get measurement values
        voltage_values = self._test_report['Vout test'][
            'voltage values']
        current_values = self._test_report['Vout test'][
            'current values']
        # Add voltage measurement values to log file
        self._logger.add_lines_to_logging_file([
            '', '', '',
            'BMS3 voltage measurement / Vout expected'])
        for voltage_value in voltage_values:
            self._logger.add_lines_to_logging_file([
                '', '', '',
                voltage_value])
        # Add current measurement values to log file
        self._logger.add_lines_to_logging_file([
            '', '', '',
            'BMS3 current consomption / '
            'BMS3 current min value / '
            'BMS3 current max value'])
        for current_value in current_values:
            self._logger.add_lines_to_logging_file([
                '', '', '',
                current_value])

        # Current consomption in sleep mode
        self._logger.add_lines_to_logging_file([
            '', 'Current consomption in sleep mode',
            self._test_report['Current consomption in sleep mode']['status'],
            'BMS3 current consomption / '
            'BMS3 current min value / '
            'BMS3 current max value'])
        self._logger.add_lines_to_logging_file([
            '', '',
            self._test_report['Current consomption in sleep mode']['value']
            ])

        # Battery charge
        self._logger.add_lines_to_logging_file([
            '', 'Battery charge',
            self._test_report['Battery charge']['status'],
            self._test_report['Battery charge']['value']
            ])

        # LED colors
        self._logger.add_lines_to_logging_file([
            '', 'LED colors', 
            self._test_report['LED colors']['status']])
        self._logger.add_lines_to_logging_file([
            '', '', 'RED',
            self._test_report['LED colors']['status_red']])
        self._logger.add_lines_to_logging_file([
            '', '', 'GREEN',
            self._test_report['LED colors']['status_green']])
        self._logger.add_lines_to_logging_file([
            '', '', 'BLUE',
            self._test_report['LED colors']['status_blue']])

        # Initialize report for next test
        self._init_test_report()

    def _test_status(self):
        if (
                self._test_report[
                    'Battery voltage measurement']['values'] == 'Test OK'
                and
                self._test_report['Vout test']['values'] == 'Test OK'
                and
                self._test_report[
                    'Current consomption in sleep mode'][
                        'values'] == 'Test OK'
                and
                self._test_report['Battery charge']['values'] == 'Test OK'
                and
                self._test_report['LED colors']['status_red'] == 'Test OK'
                and
                self._test_report['LED colors']['status_green'] == 'Test OK'
                and
                self._test_report['LED colors']['status_blue'] == 'Test OK'):
            return 'Test OK'
        else:
            return 'Test NOK'

    # HAL
    def _set_hal(self):
        self._relay_tenma_alim = {
            'board': "C", 'relay_number': 1,
            'state': State.Disable}
        self._relay_isolated_alim = {
            'board': "C", 'relay_number': 2,
            'state': State.Disable}
        self._relay_usb_vcc = {
            'board': "C", 'relay_number': 3,
            'state': State.Disable}
        self._relay_usb_ground = {
            'board': "C", 'relay_number': 4,
            'state': State.Disable}
        self._relay_push_in = {
            'board': "C", 'relay_number': 5,
            'state': State.Disable}
        self._relay_jmp_18_v = {
            'board': "C", 'relay_number': 6,
            'state': State.Disable}
        self._relay_current_measurement_in = {
            'board': "C", 'relay_number': 7,
            'state': State.Disable}
        self._relay_current_measurement_out = {
            'board': "C", 'relay_number': 8,
            'state': State.Disable}
        self._relay_high_load = {
            'board': "D", 'relay_number': 1,
            'state': State.Disable}
        self._relay_low_load_9_V = {
            'board': "D", 'relay_number': 2,
            'state': State.Disable}
        self._relay_debug_rx = {
            'board': "D", 'relay_number': 3,
            'state': State.Disable}
        self._relay_debug_tx = {
            'board': "D", 'relay_number': 4,
            'state': State.Disable}
        self._relay_bms3_battery_measurement_minus = {
            'board': "D", 'relay_number': 5,
            'state': State.Disable}
        self._relay_bms3_battery_measurement_plus = {
            'board': "D", 'relay_number': 6,
            'state': State.Disable}
        self._relay_v_out_measurement_minus = {
            'board': "D", 'relay_number': 7,
            'state': State.Disable}
        self._relay_v_out_measurement_plus = {
            'board': "D", 'relay_number': 8,
            'state': State.Disable}
        self._relay_swclk = {
            'board': "B", 'relay_number': 1,
            'state': State.Disable}
        self._relay_nrst = {
            'board': "B", 'relay_number': 2,
            'state': State.Disable}
        self._relay_swdio = {
            'board': "B", 'relay_number': 3,
            'state': State.Disable}
        self._relay_2V5 = {
            'board': "B", 'relay_number': 4,
            'state': State.Disable}
        self._relay_gnd = {
            'board': "B", 'relay_number': 5,
            'state': State.Disable}
        self._relay_low_load_18_V = {
            'board': "B", 'relay_number': 6,
            'state': State.Disable}
        self._relay_list = [
            self._relay_tenma_alim,
            self._relay_isolated_alim,
            self._relay_usb_vcc,
            self._relay_usb_ground,
            self._relay_push_in,
            self._relay_jmp_18_v,
            self._relay_current_measurement_in,
            self._relay_current_measurement_out,
            self._relay_high_load,
            self._relay_low_load_9_V,
            self._relay_debug_rx,
            self._relay_debug_tx,
            self._relay_bms3_battery_measurement_minus,
            self._relay_bms3_battery_measurement_plus,
            self._relay_v_out_measurement_minus,
            self._relay_v_out_measurement_plus,
            self._relay_swclk,
            self._relay_nrst,
            self._relay_swdio,
            self._relay_2V5,
            self._relay_gnd,
            self._relay_low_load_18_V
        ]
        self._set_bench_state_variables()

    def _activate_relay(self, relay):
        relay['state'] = State.Enable
        self._control_relay.manage_relay(
            relay['board'],
            relay['relay_number'],
            relay['state'])

    def _desactivate_relay(self, relay):
        relay['state'] = State.Disable
        self._control_relay.manage_relay(
            relay['board'],
            relay['relay_number'],
            relay['state'])

    def _set_bench_state_variables(self):
        self._tenma_alim_state = ConnectionState.Disconnected
        self._isolated_alim_state = ConnectionState.Disconnected
        self._tenma_dc_power_state = State.Disable

    # BMS3 interface
    def _load_firmware(self, firmware_label):
        self.connect_tenma_alim()
        self._tenma_dc_set_voltage(3333)
        self._tenma_dc_power_on()
        self.press_push_in_button()
        self.connect_reprog()
        process_return, std_out = self._bms3_interface.write(firmware_label)
        self.disconnect_reprog()
        self.release_push_in_button()
        self._tenma_dc_power_off()
        return process_return, std_out

    def _get_bms3_voltage_measurement(self, count=3) -> int:
        self.connect_debug_tx()
        self.connect_debug_rx()
        voltage_measurement = self._bms3_interface.get_measurement()
        if voltage_measurement == INVALID_VALUE and count > 0:
            self.disconnect_debug_rx()
            sleep(0.5)
            voltage_measurement = \
                self._get_bms3_voltage_measurement(count=count-1)
        self.disconnect_debug_rx()
        self.disconnect_debug_tx()
        return voltage_measurement

    def _set_firmware_label(self):
        self._firmware_files_list = self._bms3_interface.get_firmware_files_list()
        # Keep only '.bin' file(s)
        for firmware in self._firmware_files_list.copy():
            if not firmware[-4:] == '.bin':
                self._firmware_files_list.remove(firmware)
        # Removed '.bin' extention
        for index, firmware in enumerate(self._firmware_files_list):
            self._firmware_files_list[index] = \
                self._firmware_files_list[index][:-4]
        self._ask_firmware_choice()

    def _ask_firmware_choice(self):
        # Display menu choice
        while True:
            self._display_menu()
            answer = input('\n\tQuel est votre choix ?\t').upper()
            if answer in self.menu.keys():
                break
        if answer == 'N':
            self._load_firmware_enable = False
        else:
            self._load_firmware_enable = True
            self._firmware_label = self.menu[answer].option

    def _display_menu(self):
        self.menu = Menu()
        for firmware in self._firmware_files_list:
            self.menu.add('auto', firmware, lambda: None)
        self.menu.add('N', 'Ne pas programmer les BMS3.', lambda: None)
        key_max_lenght, option_max_lenght = self.menu.max_lenght()
        menu_frame, menu_label = menu_frame_design(
            'Liste des firmwares',
            key_max_lenght
            + option_max_lenght
            + len("  : "))
        print("\n" + menu_frame)
        print(menu_label)
        print(menu_frame)
        for key, entry in self.menu.items():
            space_before_key = " " * (key_max_lenght - len(key))
            print(f"   {space_before_key}{key}: {entry.option}")
        print(menu_frame)

    def _manage_reprog_trouble(self, process_return, std_out):
        if 'Failed to connect to target' in std_out:
            self._display_sentence_inside_frame(
                'Veuillez v??rifier les branchements du banc de test.'
            )
        elif isinstance(process_return, TimeoutExpired):
            self._display_sentences_inside_frame([
                'Reprogrammation impossible.',
                '',
                'Veuillez d??brancher/rebrancher le STLink.']
            )
        input('\n\tAppuyer sur la touche \'Entr??e\' pour continuer...')

    # HMI
    def _ask_for_board_number(self):
        self._display_sentence_inside_frame('D??but de la s??quence de test.')
        board_number = input(
            '\n\t'
            'Veuillez entrer le num??ro de la BMS3 sous test.'
            '\n\t'
            'Ou \'Quit(Q)\' pour arr??ter les s??quences de test.'
            '\n')
        if board_number == '':
            self._ask_for_board_number()
        elif board_number.lower() == 'quit' or board_number.lower() == 'q':
            self._test_in_progress = False
            self._logger.stop_logging(
                f'BMS3 - {self._test_count} tests.'
            )
            input('\n\t\t'
                  'Test termin??.'
                  '\n\n\t'
                  '(Appuyer sur la touche ENTER)')
            exit()
        else:
            if not self._check_bms3_number_format(board_number):
                self._ask_for_board_number()
            self._test_report['Board number'] = self._lot_number + '_' + board_number
            self._test_count += 1

    def _add_exception_to_log(self, err):
        self._logger.add_lines_to_logging_file([''])
        self._logger.add_lines_to_logging_file(['Exception occurs'])
        self._logger.add_lines_to_logging_file([f'{err}'])
        self._logger.add_lines_to_logging_file([f'{err.__class__}'])
        self._logger.add_lines_to_logging_file([f'{err.__doc__}'])
        self._logger.add_lines_to_logging_file([f'{err.__dict__}'])

    def _check_bms3_number_format(self, bms3_number) -> bool:
        if not bms3_number:
            message = (
                '\n\t'
                '- Format de num??ro de carte invalide -'
                '\n')
            frame = '-' * (len(message) + 4)
            print('\t', frame)
            print(message)
            print('\t', frame)
            return False
        return True

    def _display_sentence_inside_frame(self, sentence: str):
        sentence = '\t\t\t' + sentence
        frame = '*' * (16 + len(sentence))
        frame = '\n\t\t' + frame + '\n'
        print(
            frame,
            sentence,
            frame)

    def _display_sentences_inside_frame(self, sentences: list[str]):
        max_size = 0
        for sentence in sentences:
            if len(sentence) > max_size:
                max_size = len(sentence)
        for index, sentence in enumerate(sentences):
                sentences[index] = '\t\t' + sentence.center(max_size + 8)
        frame = '*' * (16 + max_size)
        frame = '\t\t' + frame
        print('\n' + frame)
        for sentence in sentences:
            print(sentence)
        print(frame + '\n')

    # Measurement tools
    def _set_multimeter(self):
        # Intialization
        self._ampmeter = None
        self._voltmeter = None
        well_connected = True
        frame = '*' * 56
        frame = '\n\t' + frame
        # Seek for Voltmeter and Ampmeter
        bcdDevices = self._get_bcd_devices()
        for bcdDevice in bcdDevices:
            tenma_multimeter = Tenma_72_7730A_manage(bcdDevice)
            tenma_multimeter.start()
            sleep(1)
            if tenma_multimeter.get_mode() == 'Current':
                self._ampmeter = tenma_multimeter
            elif tenma_multimeter.get_mode() == 'Voltage':
                self._voltmeter = tenma_multimeter
        # Check if Ampmeter is well_connected
        if self._ampmeter is None:
            well_connected = False
            print(
                frame,
                '\n\t\t'
                'V??rifier l\'installation de l\'amp??rem??tre'
                '\n\t\t'
                'et que la fonction SEND est bien activ??e.',
                frame)
        # Check if Voltmeter is well_connected
        if self._voltmeter is None:
            well_connected = False
            print(
                frame,
                '\n\t\t'
                'V??rifier l\'installation du voltm??tre'
                '\n\t\t'
                'et que la fonction SEND est bien activ??e.',
                frame)
        if not well_connected:
            print()
            system('pause')
            exit()

    def _get_bcd_devices(self) -> list[int]:
        # Seek for all connected device
        devices = usb.core.find(find_all=True)
        # Select all Tenma_72_2535
        bcdDevices = []
        for device in devices:
            if (
                    device.idProduct == ID_PRODUCT
                    and
                    device.idVendor == ID_VENDOR):
                bcdDevices.append(device.bcdDevice)
        return bcdDevices

    # Tenma DC
    def _tenma_dc_power_on(self):
        if self._tenma_dc_power_state == State.Disable:
            self._tenma_dc_power_state == State.Enable
            self._tenma_dc_power.power('ON')

    def _tenma_dc_power_off(self):
        if self._tenma_dc_power_state == State.Enable:
            self._tenma_dc_power_state == State.Disable
            self._tenma_dc_power.set_voltage(0)
            self._tenma_dc_power.power('OFF')

    def _tenma_dc_set_voltage(self, value) -> int:
        return self._tenma_dc_power.set_voltage(value)
