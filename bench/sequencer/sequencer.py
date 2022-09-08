from subprocess import CompletedProcess, TimeoutExpired
import usb.core
from time import sleep
from datetime import date
from sys import exit
from os import system
from os.path import join as os_path_join, normpath
from enum import Enum, auto

from bench.control_relay.control_relay import ControlRelay
from bench.tenma.tenma_dc_power import Tenma_72_2535_manage
from bench.tenma.tenma_multimeter import Tenma_72_7730A_manage
from bench.logger.logger import Logger
from bench.bms3_interface.bms3_command import BMS3Command, INVALID_VALUE

from bench.utils.utils import State
from bench.utils.menus import Menu, menu_frame_design

# Test parameters
VOLTAGE_MEASUREMENT_LOW_THRESHOLD = 5               # mV
VOLTAGE_MEASUREMENT_HIGH_THRESHOLD = 5              # mV
V_OUT_FOR_9_V_MIN = 8500                            # mV
V_OUT_FOR_9_V_MAX = 9500                            # mV
V_OUT_FOR_18_V_MIN = 17500                          # mV
V_OUT_FOR_18_V_MAX = 18500                          # mV
I_OUT_LOW_LOAD_FOR_9_V_MIN = 39600                  # µA
I_OUT_LOW_LOAD_FOR_9_V_MAX = 48500                  # µA
I_OUT_LOW_LOAD_FOR_18_V_MIN = 59400                 # µA
I_OUT_LOW_LOAD_FOR_18_V_MAX = 72600                 # µA
I_OUT_HIGH_LOAD_FOR_9_V_MIN = 290                   # µA
I_OUT_HIGH_LOAD_FOR_9_V_MAX = 370                   # µA
I_OUT_HIGH_LOAD_FOR_18_V_MIN = 1080                 # µA
I_OUT_HIGH_LOAD_FOR_18_V_MAX = 1320                 # µA
CURRENT_CONSOMPTION_SLEEP_MODE_LOW_THRESHOLD = 2    # µA
CURRENT_CONSOMPTION_SLEEP_MODE_HIGH_THRESHOLD = 10  # µA
BATTERY_CHARGE_CURRENT_HIGH_THRESHOLD = 270         # mA
BATTERY_CHARGE_CURRENT_LOW_THRESHOLD = 230          # mA
LED_COLOR_STEP_NUMBER = 4                           # RGB and White

# Logging
LOGGING_FOLDER = "../../logging"
DEFAULT_LOG_LABEL = 'BMS3_post_prod_test'
LOG_COLUMNS_WIDTH = [5, 35, 15, 75]

# Multimeter
ID_PRODUCT = 0xE008
ID_VENDOR = 0x1A86

# Tenma DC power
MAX_BMS3_VOLTAGE = 3500     # mV
MAX_BMS3_CURRENT = 110      # mA
MAX_USB_VOLTAGE = 5000      # mV
MAX_USB_CURRENT = 400       # mA


# Enum
class PushInState(Enum):
    NotDefined = auto()
    Automatic = auto()
    Manual = auto()


class Item(Enum):
    BMS3 = auto()
    USB = auto()


ILLEGAL_NTFS_CHARS = "[<>:/\\|?*\"]|[\0-\31]"


class Bms3Sequencer():

    ########################
    # Class Initialization #
    ########################
    def __init__(self, test_mode=False):
        # Set variables
        self._test_mode = test_mode
        self._test_in_progress = True
        self._test_count = 0
        self._test_voltage = ''
        self._lot_number = ''
        self._push_in_state = PushInState.NotDefined
        self._reprog_in_progress = False
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
        # Run tests
        self.run()

    ##################
    # Public methods #
    ##################
    def run(self):
        if self._test_mode:
            pass
        else:
            while self._test_in_progress:
                self._test_sequence()
            exit()

    # DC power
    def connect_tenma_alim(self):
        self._activate_relay(self._relay_tenma_alim)

    def disconnect_tenma_alim(self):
        self._desactivate_relay(self._relay_tenma_alim)

    def connect_isolated_alim(self):
        self._activate_relay(self._relay_isolated_alim)

    def disconnect_isolated_alim(self):
        self._desactivate_relay(self._relay_isolated_alim)

    # BMS3 input management
    def press_push_in_button(self):
        if self._push_in_state is PushInState.NotDefined:
            self._set_push_in_management()
            self.press_push_in_button()
        elif self._push_in_state is PushInState.Automatic:
            self._activate_relay(self._relay_push_in)
        else:
            if self._reprog_in_progress:
                message = (
                    '\n\t'
                    'Veuillez maintenir appuyé le bouton PUSH_IN '
                    'durant la phase de reprogrammation.')
                if 'STM32 ST_Link Utility' in self._firmware_label:
                    message = (
                        message
                        + '\n\n\t'
                        + 'Appuyer sur la touche ENTER '
                        + 'lorsque la reprogrammation est terminée.')
                else:
                    message = (
                        message
                        + '\n\t'
                        + '          Appuyer sur la touche ENTER '
                        + 'pour lancer la reprogrammation.')
            else:
                frame = (' ' * 4) + ('*' * 51)
                message = (
                    frame +
                    '\n\t'
                    '  Veuillez appuyer sur le bouton PUSH_IN.'
                    '\n\t'
                    'Appuyer sur la touche ENTER pour continuer.'
                    '\n'
                    + frame)
            input(message)
            print('...')

    def release_push_in_button(self):
        if self._push_in_state is PushInState.Automatic:
            self._desactivate_relay(self._relay_push_in)
        elif self._push_in_state is PushInState.Manual:
            if self._reprog_in_progress:
                message = (
                    '\n\t'
                    'Veuillez relacher le bouton PUSH_IN.'
                    '\n\t'
                    'Appuyer ensuite sur la touche ENTER.')
                input(message)
        else:
            # For robutness purpose,
            # since push in management shall already been done
            self._set_push_in_management()
            self.release_push_in_button()

    def bms3_wake_up(self):
        self._display_sentence_inside_frame("BMS3 - réveil.")
        self.connect_tenma_alim()
        self._tenma_dc_set_voltage(3500, Item.BMS3)
        self._tenma_dc_power_on()
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
        self._reprog_in_progress = True
        self._activate_relay(self._relay_swclk)
        self._activate_relay(self._relay_nrst)
        self._activate_relay(self._relay_swdio)
        self._activate_relay(self._relay_2V5)
        self._activate_relay(self._relay_gnd)

    def disconnect_reprog(self):
        self._reprog_in_progress = False
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
        sleep(0.5)

    def connect_high_load(self):
        self._desactivate_relay(self._relay_low_load_9_V)
        self._desactivate_relay(self._relay_low_load_18_V)
        self._activate_relay(self._relay_high_load)
        sleep(0.5)

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

    def activate_current_measurement_and_check_reset(self):
        self.activate_current_measurement()
        sleep(2)
        # Check if the BMS3 isn't reset after current measurement activation
        if self._ampmeter.get_measurement() < CURRENT_CONSOMPTION_SLEEP_MODE_LOW_THRESHOLD:
            self.press_push_in_button()
            sleep(0.5)
            return True

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

            # BMS3 load firmware if requested
            if self._load_firmware_enable:
                if 'STM32 ST_Link Utility' in self._firmware_label:
                    self._load_firmware_with_st_link_utility()
                else:
                    process_return, std_out = \
                        self._load_firmware(self._firmware_label)
                    if not isinstance(process_return, CompletedProcess):
                        self._manage_reprog_trouble(process_return, std_out)
                        raise Exception(std_out)

            # BMS3 wake up
            self.bms3_wake_up()

            # Test: Battery voltage measurement
            self._battery_voltage_measurement_test()

            # Test: Vout / Iout test
            self._v_i_out_test()

            # Test: Current consomption in sleep mode
            self._current_consomption_in_sleep_mode_test()

            # Test: Battery charge
            self._battery_charge_test()

            # Test: LED colors
            self._led_colors_test()

        except Exception as err:
            self._add_exception_to_log(err)

            # Display error
            board_number = self._test_report['Board number']
            self._display_sentences_inside_frame([
                'L\'erreur suivante est survenu :',
                f'\t{err}',
                f'\tLors du test de la carte {board_number}.'])

            # Stop logging
            self._logger.stop_logging(
                f'BMS3 - {self._test_count} tests.')
            input('\n\t\t'
                  'Test terminé.'
                  '\n\n\t'
                  '(Appuyer sur la touche ENTER)')
            # Exit prog
            self._tenma_dc_power_off()
            self.disable_all_relays()
            exit()

        finally:
            board_number = self._test_report['Board number']
            if board_number != 'Not Defined':
                # Display test result
                self._display_sentence_inside_frame(
                    f'Resultat du test de la carte {board_number} => '
                    f'{self._test_status()}')

                # Update log file
                self._update_log()

                # End test sequence
                self._tenma_dc_power_off()
                self.disable_all_relays()

        ####################################
        # Battery voltage measurement test #
        ####################################
    def _battery_voltage_measurement_test(self):
        # Init test
        self._display_sentence_inside_frame('Battery voltage measurement test')
        test_report_status = []
        voltage_to_check = [3500, 3150, 2800]
        self.connect_debug_tx()
        self.activate_bms3_battery_measurement()

        # BMS3 battery voltage measurement tests
        for voltage in voltage_to_check:
            self._tenma_dc_set_voltage(voltage, Item.BMS3)
            sleep(1)
            test_report_status.append(
                self._battery_voltage_measurement_check())

        # Evaluate test reports status
        if False not in test_report_status:
            self._test_report[
                'Battery voltage measurement'][
                    'status'] = 'Test OK'

        # End battery voltage measurement test
        self._battery_voltage_measurement_end_test()

    def _battery_voltage_measurement_check(self) -> bool:
        # Get measurements
        bms3_voltage_measurement = self._get_bms3_voltage_measurement()
        voltage_measurement = self._voltmeter.get_measurement()

        # Set voltage threshold
        measurement_high_threshold = voltage_measurement + VOLTAGE_MEASUREMENT_HIGH_THRESHOLD
        measurement_low_threshold = voltage_measurement - VOLTAGE_MEASUREMENT_LOW_THRESHOLD

        # Add measurement values to test report
        self._test_report['Battery voltage measurement']['values'].append(
            str(bms3_voltage_measurement)
            + ' / '
            + str(measurement_low_threshold)
            + ' / '
            + str(measurement_high_threshold))

        # Check measurement values
        if (
                bms3_voltage_measurement < measurement_high_threshold
                and
                bms3_voltage_measurement > measurement_low_threshold):
            return True
        else:
            return False

    def _battery_voltage_measurement_end_test(self):
        self._tenma_dc_set_voltage(3500, Item.BMS3)
        self.desactivate_bms3_battery_measurement()
        self.disconnect_debug_tx()

        # Display test reports status
        battery_voltage_report = self._test_report[
                'Battery voltage measurement']
        print("\tTest Status :\t",
              f"{battery_voltage_report['status']}")
        print('\t\tMesure BMS3 / Voltmetre')
        for value in battery_voltage_report['values']:
            print('\t\t', value, end='')
        print()

        #############
        # Vout test #
        #############
    def _v_i_out_test(self):
        # Init test
        self._display_sentence_inside_frame('Vout test')
        test_report_status = []
        self.activate_current_measurement_and_check_reset()
        self.activate_v_out_measurement()
        # Set voltage to check and current threshold
        (voltage_low_threshold,
         voltage_high_threshold,
         low_load_current_low_threshold,
         low_load_current_high_threshold,
         high_load_current_low_threshold,
         high_load_current_high_threshold) = \
            self._v_i_out_test_set_value_to_check()

        # Test low load
        self.connect_low_load()
        test_report_status.append(
            self._v_i_out_test_check(
                voltage_low_threshold,
                voltage_high_threshold,
                low_load_current_low_threshold,
                low_load_current_high_threshold))

        # Disconnect load and wait for BMS3 detection (300 ms in source code)
        self.disconnect_load()
        sleep(0.5)

        # Test high load
        self.connect_high_load()
        test_report_status.append(
            self._v_i_out_test_check(
                voltage_low_threshold,
                voltage_high_threshold,
                high_load_current_low_threshold,
                high_load_current_high_threshold))

        # Evaluate test reports status
        self._v_i_out_evaluate_test(test_report_status)

        # End Vout test
        self._v_i_out_end_test()

    def _v_i_out_test_set_value_to_check(self) -> tuple[int]:
        if self._test_voltage == '9':
            # Set voltage_to_check and current threshold for Vout = 9 V
            voltage_low_threshold = V_OUT_FOR_9_V_MIN
            voltage_high_threshold = V_OUT_FOR_9_V_MAX
            low_load_current_min = I_OUT_LOW_LOAD_FOR_9_V_MIN
            low_load_current_max = I_OUT_LOW_LOAD_FOR_9_V_MAX
            high_load_current_min = I_OUT_HIGH_LOAD_FOR_9_V_MIN
            high_load_current_max = I_OUT_HIGH_LOAD_FOR_9_V_MAX
        else:
            # Set voltage_to_check and current threshold for Vout = 18 V
            voltage_low_threshold = V_OUT_FOR_18_V_MIN
            voltage_high_threshold = V_OUT_FOR_18_V_MAX
            low_load_current_min = I_OUT_LOW_LOAD_FOR_18_V_MIN
            low_load_current_max = I_OUT_LOW_LOAD_FOR_18_V_MAX
            high_load_current_min = I_OUT_HIGH_LOAD_FOR_18_V_MIN
            high_load_current_max = I_OUT_HIGH_LOAD_FOR_18_V_MAX
        return (
            voltage_low_threshold,
            voltage_high_threshold,
            low_load_current_min,
            low_load_current_max,
            high_load_current_min,
            high_load_current_max)

    def _v_i_out_test_check(
            self,
            voltage_low_threshold: int,
            voltage_high_threshold: int,
            current_low_threshold: int,
            current_high_threshold: int) -> list:
        # Get measurements
        sleep(1)
        v_out_measurement = self._voltmeter.get_measurement()
        current_measurement = self._ampmeter.get_measurement()

        # Add measurement values to test report
        self._test_report['Vout test']['voltage values'].append(
            str(v_out_measurement)
            + ' / '
            + str(voltage_low_threshold)
            + ' / '
            + str(voltage_high_threshold))
        self._test_report['Iout test']['current values'].append(
            str(current_measurement)
            + ' / '
            + str(current_low_threshold)
            + ' / '
            + str(current_high_threshold))

        # Check measurement values
        if (
                v_out_measurement < voltage_high_threshold
                and
                v_out_measurement > voltage_low_threshold):
            v_out_check = True
        else:
            v_out_check = False

        if(
                current_measurement < current_high_threshold
                and
                current_measurement > current_low_threshold):
            i_out_check = True
        else:
            i_out_check = False
        return (v_out_check, i_out_check)

    def _v_i_out_evaluate_test(self, test_report_status: list):
        v_out_check = True
        i_out_check = True
        # Evaluate test reports status
        for v_out_status, i_out_status in test_report_status:
            if v_out_status is False:
                v_out_check = False
            if i_out_status is False:
                i_out_check = False

        if v_out_check is True:
            self._test_report[
                'Vout test'][
                    'status'] = 'Test OK'
        if i_out_check is True:
            self._test_report[
                'Iout test'][
                    'status'] = 'Test OK'

    def _v_i_out_end_test(self):
        self.disconnect_load()
        # Since the next test is "Current consomption in sleep mode"
        # The current measurement isn't desactivated.
        # self.desactivate_current_measurement()
        self.desactivate_v_out_measurement()

        # Display test reports status
        vout_report = self._test_report['Vout test']
        iout_report = self._test_report['Iout test']
        print(f"\tVout Test Status :\t{vout_report['status']}")
        print('\t\tBMS3 voltages / valeur min  / valeur max attendues')
        for voltages in vout_report['voltage values']:
            print(f'\t\t{voltages}')
        print()
        print(f"\tIout Test Status :\t{iout_report['status']}")
        print('\t\tBMS3 courant / valeur min  / valeur max attendues')
        for currents in iout_report['current values']:
            print(f'\t\t{currents}')
        print()

        ##########################################
        # Current consomption in sleep mode test #
        ##########################################
    def _current_consomption_in_sleep_mode_test(self):
        # Init test
        self._display_sentence_inside_frame('Current consomption in sleep mode test')
        self.activate_current_measurement_and_check_reset()

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

        # End test
        self._current_consomption_in_sleep_mode_end_test()

    def _current_consomption_in_sleep_mode_end_test(self):
        self.desactivate_current_measurement()

        # Display test reports status
        test_report = self._test_report['Current consomption in sleep mode']
        print(f"\tTest Status :\t{test_report['status']}")
        print('\t\tBMS3 consommation de courant / min value / max value attendues')
        print(f"\t\t{test_report['value']}")
        print()

        #######################
        # Battery charge test #
        #######################
    def _battery_charge_test(self):
        # Init test
        self._display_sentence_inside_frame('Battery charge test')
        self.connect_isolated_alim()
        self._tenma_dc_power_off()
        self.disconnect_tenma_alim()
        self.connect_usb_power()
        self._tenma_dc_set_voltage(5000, Item.USB)
        self._tenma_dc_power_on()
        sleep(1.5)

        # Get current measurement from Tenma_72_2535
        current_measurement = self._tenma_dc_power.get_current()
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

        # End test
        self._battery_charge_end_test()

    def _battery_charge_end_test(self):
        self.disconnect_usb_power()
        self._tenma_dc_power_off()
        self._tenma_dc_set_voltage(3500, Item.BMS3)
        self.connect_tenma_alim()
        self._tenma_dc_power_on()
        self.disconnect_isolated_alim()

        # Display test reports status
        test_report = self._test_report['Battery charge']
        print(f"\tTest Status :\t{test_report['status']}")
        print(f"\t\tBMS3 consommation de courant :\t{test_report['value']} mA")
        print()

        ###################
        # LED colors test #
        ###################
    def _led_colors_test(self):
        self._display_sentence_inside_frame('LED colors test')
        push_in = self.activate_current_measurement_and_check_reset()
        # Start led colors test sequence
        self._led_colors_test_sequence(push_in)
        # Evaluate test reports status
        self._led_colors_evaluate_test_reports_status()

    def _led_colors_test_sequence(self, push_in):
        # User request to start led test
        sentence = '\tSequence de test de la couleur des LED.'
        frame = '*' * (16 + len(sentence))
        frame = '\n' + frame + '\n'
        if push_in is not None:
            print(frame, sentence, frame)
            sleep(1)
        else:
            input(
                frame
                + sentence
                + frame
                + "(Appuyer sur ENTER pour lancer le test)".center(len(frame) - 2))
        # Toogle all leds
        for _ in range(LED_COLOR_STEP_NUMBER):
            self._activate_led()
            sleep(0.5)
            self._desactivate_led()
            sleep(0.2)
        # Ask for LED check
        answer = input("\n\t"
                       + "Avez-vous vu la séquence Bleu / Vert / Rouge / Blanc ?"
                       + "\n\t\t"
                       + "(Oui / Non   -   Yes / No)"
                       + "\n")
        # Evaluate answer
        if answer in 'oOyY':
            # Test OK
            self._test_report['LED colors']['status_red'] = 'Test OK'
            self._test_report['LED colors']['status_green'] = 'Test OK'
            self._test_report['LED colors']['status_blue'] = 'Test OK'
        elif answer in 'nN':
            # Test NOK, start led colors test step by step,
            # in order to evaluate which led(s) is(are) in trouble.
            self._led_colors_test_step_by_step()
        else:
            # Wrong answer, shall be in 'oOyYnN'
            print('\t\t*********************************************')
            print('\t\t*            Mauvaise réponse !             *')
            print('\t\t* Vous devez utiliser les touches o, y ou n *')
            print('\t\t*          Le test va recommencer.          *')
            print('\t\t*********************************************')
            print('')
            self._led_colors_test_sequence()

    def _led_colors_test_step_by_step(self):
        self._display_sentence_inside_frame(
            'Test de la couleur des LED (une à une).')
        # Test the blue LED
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED bleue est allumée '
            'et sa couleur conforme ?'
            '\n\t\t'
            '(Oui / Non   -   Yes / No)"\t',
            'status_blue')
        # Test the green LED
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED verte est allumée '
            'et sa couleur conforme ?'
            '\n\t\t'
            '(Oui / Non   -   Yes / No)"\t',
            'status_green')
        # Test the red LED
        self._led_colors_check(
            '\n\t'
            'Est-ce que la LED rouge est allumée '
            'et sa couleur conforme ?'
            '\n\t\t'
            '(Oui / Non   -   Yes / No)"\t',
            'status_red')

    def _led_colors_check(
            self,
            question,
            test_in_progress):
        # Activate the LED
        self._activate_led()
        # Ask for LED check
        answer = input("\n\t" + question)
        # Desactivate the LED
        self._desactivate_led()
        # Evaluate answer
        if answer in 'oOyY':
            # Test OK
            self._test_report['LED colors'][test_in_progress] = 'Test OK'
        elif answer not in 'nN':
            # Wrong answer, shall be in 'oOyYnN'
            print('\t\t*********************************************')
            print('\t\t*            Mauvaise réponse !             *')
            print('\t\t* Vous devez utiliser les touches o, y ou n *')
            print('\t\t*          Le test va recommencer.          *')
            print('\t\t*********************************************')
            # Toogle led until the previous one
            for _ in range(LED_COLOR_STEP_NUMBER - 1):
                self._activate_led()
                sleep(0.2)
                self._desactivate_led()
                sleep(0.2)
            # Restart the test from the current step
            self._led_colors_check(
                question,
                test_in_progress)

    def _activate_led(self):
        self.activate_jmp_18_v()

    def _desactivate_led(self):
        self.desactivate_jmp_18_v()

    def _led_colors_evaluate_test_reports_status(self):
        # Evaluate test reports status
        if 'Test NOK' not in (
                self._test_report['LED colors']['status_red'],
                self._test_report['LED colors']['status_green'],
                self._test_report['LED colors']['status_blue']):
            self._test_report[
                'LED colors'][
                    'status'] = 'Test OK'

    # Logging
    def _set_logger(self) -> None:
        logging_name = self._set_logging_name()
        self._logger = Logger(
            logging_name=logging_name,
            logging_folder=normpath(os_path_join(LOGGING_FOLDER, self._lot_number)),
            columns_width=LOG_COLUMNS_WIDTH)
        self._init_test_report()
        self._add_date_to_log()

    def _set_logging_name(self) -> str:
        logging_name = ILLEGAL_NTFS_CHARS
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
                + 'Entrer le type de test (9 / 18 V)'
                + '\n\t\t'
                + '1: 18 V'
                + '\n\t\t'
                + '9: 9 V'
                + '\n'
            )
            if self._test_voltage == '1':
                self._test_voltage = '18'
                print("\t\tTest des cartes en 18 V sélectionné.\n")
            elif self._test_voltage == '9':
                print("\t\tTest des cartes en 9 V sélectionné.\n")

        return logging_name + '_' + self._test_voltage + 'V'

    def _set_lot_number(self, logging_name: str) -> str:
        while(
                self._lot_number == ''
                or
                (True in [caracter in ILLEGAL_NTFS_CHARS for caracter in self._lot_number])):
            self._lot_number = input(
                '\n\t'
                'Entrer le numéro de lot :'
                '\n\t\t'
            )

        return logging_name + '_' + self._lot_number

    def _init_test_report(self):
        self._test_report = {
            'Board number': 'Not Defined',
            'Battery voltage measurement': (
                {'status': 'Test NOK',
                 'values': []}),
            'Vout test': (
                {'status': 'Test NOK',
                 'voltage values': []}),
            'Iout test': (
                {'status': 'Test NOK',
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
            'BMS3 measurement / Voltmeter (min & max value tolerance)'])
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
            self._test_report['Vout test']['status'],
            'BMS3 voltage measurement / Vout min / Vout max expected'])
        # Get measurement values
        voltage_values = self._test_report['Vout test']['voltage values']
        # Add voltage measurement values to log file
        for voltage_value in voltage_values:
            self._logger.add_lines_to_logging_file([
                '', '', '',
                voltage_value])

        # Iout test
        # Add status to log file
        self._logger.add_lines_to_logging_file([
            '', 'Iout test',
            self._test_report['Iout test']['status'],
            'BMS3 current consomption / '
            'BMS3 current min value / '
            'BMS3 current max value'])
        # Get measurement values
        current_values = self._test_report['Iout test']['current values']
        # Add current measurement values to log file
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
            '', '', '',
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
                    'Battery voltage measurement']['status'] == 'Test OK'
                and
                self._test_report['Vout test']['status'] == 'Test OK'
                and
                self._test_report[
                    'Current consomption in sleep mode'][
                        'status'] == 'Test OK'
                and
                self._test_report['Battery charge']['status'] == 'Test OK'
                and
                self._test_report['LED colors']['status_red'] == 'Test OK'
                and
                self._test_report['LED colors']['status_green'] == 'Test OK'
                and
                self._test_report['LED colors']['status_blue'] == 'Test OK'):
            return 'Test OK'
        else:
            return 'Test NOK'

    def _add_date_to_log(self):
        self._logger.add_lines_to_logging_file([''])
        self._logger.add_lines_to_logging_file([
            '',
            'Date du test :',
            date.today().strftime('%Y-%m-%d')])

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
        self._tenma_dc_power_state = State.Disable

    def _is_current_measurement_connected(self):
        return (
            self._relay_current_measurement_in['state'] == State.Enable
            and
            self._relay_current_measurement_out['state'] == State.Enable)

    # BMS3 interface
    def _load_firmware(self, firmware_label):
        self.connect_tenma_alim()
        self._tenma_dc_set_voltage(3333, Item.BMS3)
        self._tenma_dc_power_on()
        self.connect_reprog()
        self.press_push_in_button()
        process_return, std_out = self._bms3_interface.write(firmware_label)
        self.release_push_in_button()
        self.disconnect_reprog()
        self._tenma_dc_power_off()
        return process_return, std_out

    def _load_firmware_with_st_link_utility(self):
        self.connect_tenma_alim()
        self._tenma_dc_set_voltage(3333, Item.BMS3)
        self._tenma_dc_power_on()
        self.connect_reprog()
        self.press_push_in_button()
        self.disconnect_reprog()
        self._tenma_dc_power_off()
        sleep(1)

    def _get_bms3_voltage_measurement(self, count=3) -> int:
        sleep(0.3)
        self.connect_debug_rx()
        voltage_measurement = self._bms3_interface.get_measurement()
        if voltage_measurement == INVALID_VALUE and count >= 2:
            self.disconnect_debug_rx()
            voltage_measurement = \
                self._get_bms3_voltage_measurement(count=count-1)
        elif voltage_measurement == INVALID_VALUE and count >= 1:
            self._bms3_interface.seek_for_port_com()
            self.disconnect_debug_rx()
            voltage_measurement = \
                self._get_bms3_voltage_measurement(count=count-1)
        elif voltage_measurement == INVALID_VALUE and count >= 0:
            self.disconnect_debug_rx()
            voltage_measurement = \
                self._get_bms3_voltage_measurement(count=count-1)
        self.disconnect_debug_rx()
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
        self.menu.add('S',
                      'Programmer les BMS3 avec STM32 ST_Link Utility.',
                      lambda: None)
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
                'Veuillez vérifier les branchements du banc de test.')
        elif isinstance(process_return, TimeoutExpired):
            self._display_sentences_inside_frame([
                'Reprogrammation impossible.',
                '',
                'Veuillez débrancher/rebrancher le STLink.']
            )
        input('\n\tAppuyer sur la touche \'Entrée\' pour continuer...')

    def _set_push_in_management(self):
        # Managed the case where current measurement has been requested
        # before push_in_state has been set.
        current_measurement_connected = self._is_current_measurement_connected()
        if not current_measurement_connected:
            self.activate_current_measurement()
        # Check if push_in in automatic mode worked
        self._activate_relay(self._relay_push_in)
        sleep(2)
        current_measurement = self._ampmeter.get_measurement()
        self._desactivate_relay(self._relay_push_in)
        if current_measurement > CURRENT_CONSOMPTION_SLEEP_MODE_LOW_THRESHOLD:
            self._push_in_state = PushInState.Automatic
        else:
            self._push_in_state = PushInState.Manual
        # Desactivate current measurement if it wasn't already connected
        if not current_measurement_connected:
            self.desactivate_current_measurement()

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
            self._tenma_dc_power_off()
            self.disable_all_relays()
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
                    device.idVendor == ID_VENDOR
                    and
                    device.bcdDevice not in bcdDevices):
                bcdDevices.append(device.bcdDevice)
        return bcdDevices

    # Tenma DC
    def _tenma_dc_power_on(self):
        if self._tenma_dc_power_state == State.Disable:
            self._tenma_dc_power_state = State.Enable
            self._tenma_dc_power.power('ON')

    def _tenma_dc_power_off(self):
        if self._tenma_dc_power_state == State.Enable:
            self._tenma_dc_power_state = State.Disable
            self._tenma_dc_power.set_voltage(0)
            self._tenma_dc_power.power('OFF')

    def _tenma_dc_set_voltage(self, value: int, item: Item) -> int:
        if item == Item.BMS3:
            max_voltage = MAX_BMS3_VOLTAGE
            max_current = MAX_BMS3_CURRENT
        else:
            max_voltage = MAX_USB_VOLTAGE
            max_current = MAX_USB_CURRENT
        value = min(max_voltage, value)
        self._tenma_dc_power.set_current(max_current)
        return self._tenma_dc_power.set_voltage(value)
