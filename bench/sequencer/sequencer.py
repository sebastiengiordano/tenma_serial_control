import threading
from time import sleep

from bench.control_relay.control_relay import ControlRelay
from bench.tenma.tenma_dc_power import Tenma_72_2535_manage
from bench.tenma.tenma_multimeter import Tenma_72_7730A_manage
from bench.logger.logger import Logger
from bench.bms3_interface.bms3_command import BMS3Command

from bench.utils.utils import State, ConnectionState

MEASUREMENT_TOLERANCE = 10

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

    def press_push_in_button(self):
        self._activate_relay(self._relay_push_in)

    def release_push_in_button(self):
        self._desactivate_relay(self._relay_push_in)

    def bms3_wake_up(self):
        self.connect_tenma_alim()
        self._tenma_dc_power_on()
        self._tenma_dc_set_voltage(3500)
        self.press_push_in_button()
        sleep(500)
        self.release_push_in_button()

    def activate_jmp_18_v(self):
        self._activate_relay(self._relay_jmp_18_v)

    def desactivate_jmp_18_v(self):
        self._desactivate_relay(self._relay_jmp_18_v)

    def connect_low_load(self):
        self._activate_relay(self._relay_low_load)
        self._desactivate_relay(self._relay_high_load)

    def connect_high_load(self):
        self._activate_relay(self._relay_high_load)
        self._desactivate_relay(self._relay_low_load)

    def disconnect_load(self):
        self._desactivate_relay(self._relay_low_load)
        self._desactivate_relay(self._relay_high_load)

    def activate_current_measurement(self):
        self._activate_relay(self._relay_current_measurement_in)
        self._activate_relay(self._relay_current_measurement_out)

    def desactivate_current_measurement(self):
        self._desactivate_relay(self._relay_current_measurement_in)
        self._desactivate_relay(self._relay_current_measurement_out)

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

    def disable_all_relay(self):
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
            self.disable_all_relay()

    def _battery_voltage_measurement_test(self):
        self.bms3_wake_up()
        bms3_volt_measurement = self._get_bms3_voltage_measurement()
        volt_measurement = self._voltmeter.get_measurement()
        measurement_threshold = volt_measurement * MEASUREMENT_TOLERANCE / 100
        if (
                bms3_volt_measurement < volt_measurement + measurement_threshold
                and
                bms3_volt_measurement > volt_measurement - measurement_threshold):
            self._test_report['Battery voltage measurement'] = 'Test OK'

    def _preamplifier_test(self):
        raise NotImplementedError

    def _current_consomption_in_sleep_mode_test(self):
        raise NotImplementedError

    def _battery_charge_test(self):
        raise NotImplementedError

    def _led_colors_test(self):
        raise NotImplementedError

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

    def _init_test_report(self):
        return {
            'Board number': 'Not Defined',
            'Battery voltage measurement': 'Test NOK',
            'Preamplifier test': 'Test NOK',
            'Current consomption in sleep mode': 'Test NOK',
            'Battery charge': 'Test NOK',
            'LED colors': 'Test NOK'
        }

    def _update_log(self):
        self._logger.add_lines_to_logging_file([''])
        for key, value in self._test_report.items():
            self._logger.add_lines_to_logging_file(['', key, value])
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
        self.connect_reprog()
        if self._bms3_state == ConnectionState.Disconnected:
            self._bms3_interface.connect_to_bms3()
            self._bms3_state = ConnectionState.Connected
        self._bms3_interface.load_firmware(firmware_label)
        self.disconnect_reprog()

    def _get_bms3_voltage_measurement(self):
        self.connect_debug_rx()
        self.connect_debug_tx()
        raise NotImplementedError
        self.disconnect_debug_rx()
        self.disconnect_debug_tx()

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

    def _check_bms3_number_format(self, bms3_number):
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
            self._tenma_dc_power.set_voltage(0)
            self._tenma_dc_power.power('ON')

    def _tenma_dc_power_off(self):
        if self._tenma_dc_power_state == State.Enable:
            self._tenma_dc_power_state == State.Disable
            self._tenma_dc_power.set_voltage(0)
            self._tenma_dc_power.power('OFF')

    def _tenma_dc_set_voltage(self, value):
        return self._tenma_dc_power.set_voltage(value)
