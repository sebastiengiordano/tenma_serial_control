import threading
from time import sleep

from bench.control_relay.control_relay import ControlRelay
from bench.tenma.tenma_dc_power import Tenma_72_2535_manage
from bench.tenma.tenma_multimeter import Tenma_72_7730A_manage
from bench.logger.logger import Logger
from bench.bms3_interface.bms3_command import BMS3Command

from bench.utils.utils import State, ConnectionState

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
LOG_COLUMNS_WIDTH = [40]*10


class Bms3Sequencer(threading.Thread):

    ########################
    # Class Initialization #
    ########################
    def __init__(self):
        threading.Thread.__init__(self)
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
        # Set other variables
        self._test_in_progress = True
        self._test_count = 0

    ##################
    # Public methods #
    ##################
    def start(self):
        while self._test_in_progress:
            self._test_sequence()

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

    def disconnect_reprog(self):
        self._desactivate_relay(self._relay_swclk)
        self._desactivate_relay(self._relay_nrst)
        self._desactivate_relay(self._relay_swdio)

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

            # BMS3 load "post prod test" firmware
            self._load_firmware('BMS_3.0_v3_v01.11_post_prod_test')

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

            # BMS3 load "customer" firmware BMS_3.0_v3_v01.11
            self._load_firmware('BMS_3.0_v3_v01.11')

        except Exception as err:
            self._add_exception_to_log(err)

        finally:
            # Update log file
            self._update_log()

            # Disable all relay
            self.disable_all_relays()

    def _battery_voltage_measurement_test(self):
        # Init test
        test_report_status = []
        voltage_to_check = [
            3500,
            3150,
            2800]

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
        voltage_measurement = self._voltmeter.get_measurement()
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

    def _preamplifier_test(self):
        # Init test
        test_report_status = []
        self.activate_current_measurement()
        # Need to know if the bench used a third multimeter
        # or if it used more relay in order to used only one multimeter
        raise NotImplementedError

        # Connected low load and check BMS3 behavior
        self.connect_low_load()
        sleep(.5)
        test_report_status.append(
            self._preamplifier_test_check(
                9000,
                LOW_LOAD_CURRENT_LOW_THRESHOLD,
                LOW_LOAD_CURRENT_HIGH_THRESHOLD))

        # Disconnected low load
        self.disconnect_load()
        sleep(.5)

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
        sleep(.5)

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

    def _current_consomption_in_sleep_mode_test(self):
        # Get measurement
        current_measurement = self._ampmeter.get_measurement()

        # Add measurement values to test report
        self._test_report['Current consomption in sleep mode']['value'].append(
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

    def _led_colors_test(self):
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED bleue est allumée '
            'et sa couleur conforme ? (y/n)',
            'status_blue')
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED verte est allumée '
            'et sa couleur conforme ? (y/n)',
            'status_green')
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED rouge est allumée '
            'et sa couleur conforme ? (y/n)',
            'status_red')

    def _led_colors_check(
            self,
            question,
            test_in_progress):
        # Ask for LED check
        answer = input(question)
        # Evaluate answer
        if answer in 'yY':
            # Test OK
            self._test_report['LED colors'][test_in_progress] = 'Test OK'
        elif answer not in 'nN':
            # Wrong answer, shall be in 'yYnN'
            self._led_colors_check(
                question,
                test_in_progress)

    # Logging
    def _set_logger(self):
        logging_name = input(
            '\t'
            'Entrer le nom de la série de test.'
            '\n\t'
            'Rmq: ou taper sur ENTER pour utiliser le nom'
            '\n\t'
            f'par défaut: {DEFAULT_LOG_LABEL}.'
        )
        self._logger = Logger(
            logging_name=logging_name,
            logging_folder=LOGGING_FOLDER,
            columns_width=LOG_COLUMNS_WIDTH)
        self._test_report = self._init_test_report()

    def _init_test_report(self) -> dict:
        return {
            'Board number': 'Not Defined',
            'Battery voltage measurement': (
                {'status': 'Test NOK',
                 'values': []}),
            'Preamplifier test': (
                {'status': 'Test NOK',
                 'values': []}),
            'Current consomption in sleep mode': (
                {'status': 'Test NOK',
                 'value': -1}),
            'Battery charge': (
                {'status': 'Test NOK',
                 'value': -1}),
            'LED colors': {
                'status_red': 'Test NOK',
                'status_green': 'Test NOK',
                'status_blue': 'Test NOK'}
        }

    def _update_log(self):
        self._logger.add_lines_to_logging_file([''])
        # Board number
        self._logger.add_lines_to_logging_file([
            '', 'Board number',
            self._test_report['Board number']])

        # Battery voltage measurement
        # Add status to log file
        self._logger.add_lines_to_logging_file([
            '', 'Battery voltage measurement',
            self._test_report['Battery voltage measurement']['status']])
        # Get measurement values
        values = self._test_report['Battery voltage measurement']['values']
        # Add measurement values to log file
        self._logger.add_lines_to_logging_file([
            '', '', '',
            'BMS3 measurement / Voltmeter measurement'])
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
            self._test_report['Current consomption in sleep mode']['value']
            ])

        # Battery charge
        self._logger.add_lines_to_logging_file([
            '', 'Battery charge',
            self._test_report['Battery charge']['status'],
            self._test_report['Battery charge']['value']
            ])

        # LED colors
        self._logger.add_lines_to_logging_file(['', 'LED colors'])
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

    # HAL
    def _set_hal(self):
        self._relay_tenma_alim = {
            'board': "AC", 'relay_number': 1,
            'state': State.Disable}
        self._relay_isolated_alim = {
            'board': "AC", 'relay_number': 2,
            'state': State.Disable}
        self._relay_usb_vcc = {
            'board': "AC", 'relay_number': 3,
            'state': State.Disable}
        self._relay_usb_ground = {
            'board': "AC", 'relay_number': 4,
            'state': State.Disable}
        self._relay_push_in = {
            'board': "AC", 'relay_number': 5,
            'state': State.Disable}
        self._relay_jmp_18_v = {
            'board': "AC", 'relay_number': 6,
            'state': State.Disable}
        self._relay_current_measurement_in = {
            'board': "AC", 'relay_number': 7,
            'state': State.Disable}
        self._relay_current_measurement_out = {
            'board': "AC", 'relay_number': 8,
            'state': State.Disable}
        self._relay_low_load = {
            'board': "AD", 'relay_number': 1,
            'state': State.Disable}
        self._relay_high_load = {
            'board': "AD", 'relay_number': 2,
            'state': State.Disable}
        self._relay_debug_tx = {
            'board': "AD", 'relay_number': 4,
            'state': State.Disable}
        self._relay_debug_rx = {
            'board': "AD", 'relay_number': 5,
            'state': State.Disable}
        self._relay_swclk = {
            'board': "AD", 'relay_number': 6,
            'state': State.Disable}
        self._relay_nrst = {
            'board': "AD", 'relay_number': 7,
            'state': State.Disable}
        self._relay_swdio = {
            'board': "AD", 'relay_number': 8,
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
            self._relay_debug_tx,
            self._relay_debug_rx,
            self._relay_swclk,
            self._relay_nrst,
            self._relay_swdio
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
        self._bms3_state = ConnectionState.Disconnected

    # BMS3 interface
    def _load_firmware(self, firmware_label):
        self.connect_tenma_alim()
        self._tenma_dc_set_voltage(3333)
        self._tenma_dc_power_on()
        self.press_push_in_button()
        self.connect_reprog()
        if self._bms3_state == ConnectionState.Disconnected:
            self._bms3_interface.connect_to_bms3()
            self._bms3_state = ConnectionState.Connected
        self._bms3_interface.load_firmware(firmware_label)
        self.disconnect_reprog()
        self.release_push_in_button()
        self._tenma_dc_power_off()

    def _get_bms3_voltage_measurement(self) -> int:
        self.connect_debug_rx()
        self.connect_debug_tx()
        voltage_measurement = self._bms3_interface.read_debug_tx()
        self.disconnect_debug_rx()
        self.disconnect_debug_tx()
        return int(voltage_measurement)

    # HMI
    def _ask_for_board_number(self):
        board_number = input(
            '\n\t'
            'Veuillez entrer le numéro de la BMS3 sous test.'
            '\n\t'
            'Ou \'Quit\' pour arrêter les séquences de test.')
        if board_number == '':
            self._ask_for_board_number()
        elif board_number.lower() == 'quit':
            self._logger.stop_logging(
                f'BMS3 - {self._test_count} post-prod tests.'
            )
            self._tenma_dc_power.power('OFF')
            self._tenma_dc_power.disconnect()
            self._ampmeter.kill()
            self._voltmeter.kill()
            print('\n\t\t'
                  'Test end.')
        else:
            if not self._check_bms3_number_format():
                self._ask_for_board_number()
            self._test_report['Board number'] = board_number

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

    # Measurement tools
    def _set_multimeter(self):
        # Seek for Voltmeter and Ampmeter
        tenma_multimeter = Tenma_72_7730A_manage(0x1200)
        if tenma_multimeter.get_mode() == 'Current':
            self._ampmeter = tenma_multimeter
            self._voltmeter = Tenma_72_7730A_manage(0x1400)
        else:
            self._voltmeter = tenma_multimeter
            self._ampmeter = Tenma_72_7730A_manage(0x1400)
        well_connected = True
        if not self._ampmeter.get_mode() == 'Current':
            well_connected = False
            print('Vérifier l\'installation de l\'ampèremètre\n'
                  'et que la fonction SEND est bien activée.')
        if not self._voltmeter.get_mode() == 'Voltage':
            well_connected = False
            print('Vérifier l\'installation du voltmètre\n'
                  'et que la fonction SEND est bien activée.')
            if not well_connected:
                input()
                raise SystemExit

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
