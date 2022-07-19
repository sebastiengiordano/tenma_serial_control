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

VOLTAGE_MEASUREMENT_TOLERANCE = 5               # %
PREAMP_VOLTAGE_TOLERANCE = 100                  # mV
NO_LOAD_CURRENT_HIGH_THRESHOLD = 0.01           # mA
NO_LOAD_CURRENT_LOW_THRESHOLD = 0.001           # mA
LOW_LOAD_CURRENT_HIGH_THRESHOLD = 28            # mA
LOW_LOAD_CURRENT_LOW_THRESHOLD = 32             # mA
HIGH_LOAD_CURRENT_HIGH_THRESHOLD = 1            # mA
HIGH_LOAD_CURRENT_LOW_THRESHOLD = 1.1           # mA
HIGH_LOAD_CURRENT_HIGH_THRESHOLD = 1            # mA
HIGH_LOAD_CURRENT_LOW_THRESHOLD = 1.1           # mA
BATTERY_CHARGE_CURRENT_HIGH_THRESHOLD = -50     # mA
BATTERY_CHARGE_CURRENT_LOW_THRESHOLD = -100     # mA

LOGGING_FOLDER = "../../logging"
DEFAULT_LOG_LABEL = 'BMS3_post_prod_test'
LOG_COLUMNS_WIDTH = [5, 35, 10, 75]

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

    def disconnect_debug_tx(self):
        self._desactivate_relay(self._relay_debug_tx)

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

    # Connect/disconnected preamplifier
    def connect_low_load(self):
        self._activate_relay(self._relay_low_load)
        self._desactivate_relay(self._relay_high_load)

    def connect_high_load(self):
        self._activate_relay(self._relay_high_load)
        self._desactivate_relay(self._relay_low_load)

    def disconnect_load(self):
        self._desactivate_relay(self._relay_low_load)
        self._desactivate_relay(self._relay_high_load)

    # Connect/disconnected measurement tools
    def activate_current_measurement(self):
        self._activate_relay(self._relay_current_measurement_in)
        self._activate_relay(self._relay_current_measurement_out)

    def desactivate_current_measurement(self):
        self._desactivate_relay(self._relay_current_measurement_in)
        self._desactivate_relay(self._relay_current_measurement_out)

    def activate_bms3_battery_measurement(self):
        self.desactivate_preamplifier_measurement()
        self._activate_relay(self._relay_bms3_battery_measurement_minus)
        self._activate_relay(self._relay_bms3_battery_measurement_plus)

    def desactivate_bms3_battery_measurement(self):
        self._desactivate_relay(self._relay_bms3_battery_measurement_minus)
        self._desactivate_relay(self._relay_bms3_battery_measurement_plus)

    def activate_preamplifier_measurement(self):
        self.desactivate_bms3_battery_measurement()
        self._activate_relay(self._relay_preamplifier_measurement_minus)
        self._activate_relay(self._relay_preamplifier_measurement_plus)

    def desactivate_preamplifier_measurement(self):
        self._desactivate_relay(self._relay_preamplifier_measurement_minus)
        self._desactivate_relay(self._relay_preamplifier_measurement_plus)

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

    # Test procedures
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

            # Test: Preamplifier test
            self._preamplifier_test()

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
                  'Test terminé.'
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

        # Battery voltage measurement test
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

        # Preamplifier test
    def _preamplifier_test(self):
        # Init test
        test_report_status = []
        self.activate_current_measurement()
        self.activate_preamplifier_measurement()

        # Connected low load and check BMS3 behavior
        self.connect_low_load()
        sleep(.5)
        test_report_status.append(
            self._preamplifier_test_check(
                9000,
                LOW_LOAD_CURRENT_LOW_THRESHOLD,
                LOW_LOAD_CURRENT_HIGH_THRESHOLD))

        # Disconnected low load and check BMS3 behavior
        self.disconnect_load()
        self.activate_bms3_battery_measurement()
        sleep(.5)
            # Get battery voltage in order to check that its
            # the same voltage at preamplifier output
        voltage_measurement = self._voltmeter.get_measurement()
        self.activate_preamplifier_measurement()
        sleep(.5)
        test_report_status.append(
            self._preamplifier_test_check(
                voltage_measurement,
                NO_LOAD_CURRENT_LOW_THRESHOLD,
                NO_LOAD_CURRENT_HIGH_THRESHOLD))

        # Connected high load and check BMS3 behavior
        self.connect_high_load()
        sleep(.5)
        test_report_status.append(
            self._preamplifier_test_check(
                9000,
                HIGH_LOAD_CURRENT_LOW_THRESHOLD,
                HIGH_LOAD_CURRENT_HIGH_THRESHOLD))

        # Evaluate test reports status
        if False not in test_report_status:
            self._test_report[
                'Preamplifier test'][
                    'status'] = 'Test OK'

        # End preamplifier test
        self.disconnect_load()

    def _preamplifier_test_check(
            self,
            voltage_to_check,
            current_low_threshold,
            current_high_threshold):
        # Get measurements
        voltage_measurement = self._voltmeter.get_measurement()
        current_measurement = self._ampmeter.get_measurement()

        # Set voltage threshold
        voltage_high_threshold = voltage_to_check + PREAMP_VOLTAGE_TOLERANCE
        voltage_low_threshold = voltage_to_check - PREAMP_VOLTAGE_TOLERANCE

        # Add measurement values to test report
        self._test_report['Preamplifier test']['voltage values'].append(
            str(voltage_measurement)
            + ' / '
            + str(voltage_to_check))
        self._test_report['Preamplifier test']['current values'].append(
            str(current_measurement)
            + ' / '
            + str(current_low_threshold)
            + ' / '
            + str(current_high_threshold))

        # Check measurement values
        if (
                (
                    voltage_measurement < voltage_high_threshold
                    and
                    voltage_measurement > voltage_low_threshold)
                and
                (
                    current_measurement < current_high_threshold
                    and
                    current_measurement > current_low_threshold
                )):
            return True
        else:
            return False

        # Current consomption in sleep mode test
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
            + str(NO_LOAD_CURRENT_LOW_THRESHOLD)
            + ' / '
            + str(NO_LOAD_CURRENT_HIGH_THRESHOLD))

        # Check measurement values
        if (
                current_measurement < NO_LOAD_CURRENT_HIGH_THRESHOLD
                and
                current_measurement > NO_LOAD_CURRENT_LOW_THRESHOLD):
            self._test_report[
                'Current consomption in sleep mode'][
                    'status'] = 'Test OK'

        # Battery charge test
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

        # LED colors test
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
            'Est-ce que la LED bleue est allumée '
            'et sa couleur conforme ? (y/n)\t',
            'status_blue')
        # Test the green LED
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED verte est allumée '
            'et sa couleur conforme ? (y/n)\t',
            'status_green')
        # Test the red LED
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED rouge est allumée '
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
            'Entrer le nom de la série de test.'
            '\n\n\t'
            'Rmq: ou taper sur ENTER pour utiliser'
            '\n\t'
            f'le nom par défaut: {DEFAULT_LOG_LABEL}.'
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
                'Entrer le numéro de lot :'
                '\n\t\t'
            )
         

        return logging_name + '_' + self._lot_number

    def _init_test_report(self) -> dict:
        return {
            'Board number': 'Not Defined',
            'Battery voltage measurement': (
                {'status': 'Test NOK',
                 'values': []}),
            'Preamplifier test': (
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

        # Preamplifier test
        # Add status to log file
        self._logger.add_lines_to_logging_file([
            '', 'Preamplifier test',
            self._test_report['Preamplifier test']['status']])
        # Get measurement values
        voltage_values = self._test_report['Preamplifier test'][
            'voltage values']
        current_values = self._test_report['Preamplifier test'][
            'current values']
        # Add voltage measurement values to log file
        self._logger.add_lines_to_logging_file([
            '', '', '',
            'BMS3 voltage measurement / preamplifier voltage expected'])
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
                self._test_report['Preamplifier test']['values'] == 'Test OK'
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
        self._relay_low_load = {
            'board': "D", 'relay_number': 1,
            'state': State.Disable}
        self._relay_high_load = {
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
        self._relay_preamplifier_measurement_minus = {
            'board': "D", 'relay_number': 7,
            'state': State.Disable}
        self._relay_preamplifier_measurement_plus = {
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
        self._relay_list = [
            self._relay_tenma_alim,
            self._relay_isolated_alim,
            self._relay_usb_vcc,
            self._relay_usb_ground,
            self._relay_push_in,
            self._relay_jmp_18_v,
            self._relay_current_measurement_in,
            self._relay_current_measurement_out,
            self._relay_low_load,
            self._relay_high_load,
            self._relay_debug_rx,
            self._relay_debug_tx,
            self._relay_bms3_battery_measurement_minus,
            self._relay_bms3_battery_measurement_plus,
            self._relay_preamplifier_measurement_minus,
            self._relay_preamplifier_measurement_plus,
            self._relay_swclk,
            self._relay_nrst,
            self._relay_swdio,
            self._relay_2V5,
            self._relay_gnd
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
                'Veuillez vérifier les branchements du banc de test.'
            )
        elif isinstance(process_return, TimeoutExpired):
            self._display_sentences_inside_frame([
                'Reprogrammation impossible.',
                '',
                'Veuillez débrancher/rebrancher le STLink.']
            )
        input('\n\tAppuyer sur la touche \'Entrée\' pour continuer...')

    # HMI
    def _ask_for_board_number(self):
        self._display_sentence_inside_frame('Début de la séquence de test.')
        board_number = input(
            '\n\t'
            'Veuillez entrer le numéro de la BMS3 sous test.'
            '\n\t'
            'Ou \'Quit(Q)\' pour arrêter les séquences de test.'
            '\n')
        if board_number == '':
            self._ask_for_board_number()
        elif board_number.lower() == 'quit' or board_number.lower() == 'q':
            self._test_in_progress = False
            self._logger.stop_logging(
                f'BMS3 - {self._test_count} tests.'
            )
            input('\n\t\t'
                  'Test terminé.'
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
                '- Format de numéro de carte invalide -'
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
                'Vérifier l\'installation de l\'ampèremètre'
                '\n\t\t'
                'et que la fonction SEND est bien activée.',
                frame)
        # Check if Voltmeter is well_connected
        if self._voltmeter is None:
            well_connected = False
            print(
                frame,
                '\n\t\t'
                'Vérifier l\'installation du voltmètre'
                '\n\t\t'
                'et que la fonction SEND est bien activée.',
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
