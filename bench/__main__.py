from .tenma.temna_dc_power import Tenma_72_2535_manage
from .tenma.tenma_multimeter import MeasurementFunction, Tenma_72_7730A_manage

from os.path import dirname, join as os_path_join, exists, isfile
from os import listdir

import csv
from datetime import date

from .logger.logger import Logger


def files_in_folder(folder_path: str ) -> list:
    '''Return the list of all files in folder_path and its subfolder'''
    files_in_folder_path = []
    # Loop on all files or directories inside folder_path
    for file_or_dir in listdir(folder_path):
        file_or_dir_path = os_path_join(folder_path, file_or_dir)
        # If file_or_dir is a file
        if isfile(file_or_dir_path):
            # Add it to the files list
            files_in_folder_path.append(file_or_dir)
        else:
            # Loop inside the subfolder to find all files
            files_in_subfolder = files_in_folder(file_or_dir_path)
            # Add relative path from folder_path
            for index, file in enumerate(files_in_subfolder.copy()):
                files_in_subfolder[index] = file_or_dir + "/" + file
            # Add this files to the files list
            files_in_folder_path += files_in_subfolder
    return files_in_folder_path


def get_logging_folder():
    module_dir = dirname(__file__)
    return os_path_join(
        module_dir,
        "../logging")


def get_logging_files_list():
    logging_folder_path = get_logging_folder()
    logging_files_list = files_in_folder(logging_folder_path)
    return logging_files_list


def generate_logging_file_path() -> None:
    '''Generate a new default logging file path'''
    logging_files_list = get_logging_files_list()
    logging_folder_path = get_logging_folder()
    today = date.today()
    today_in_str = (
        str(today.year) + "_"
        + str(today.month) + "_"
        + str(today.day)
        )
    for i in range(10000):
        file_name = (
            today_in_str
            + "_multimeter_Measurements_"
            + _file_number_padding(i)
            )
        file_name_csv = file_name  + ".csv"
        file_name_xlsx = file_name + ".xlsx"
        if (
                file_name_csv not in logging_files_list
                and
                file_name_xlsx not in logging_files_list):
            return os_path_join(
            logging_folder_path,
            file_name_csv)


def add_lines_to_logging_file(logging_file_path: str, data: list):
    with open(logging_file_path,'a', newline='') as fd:
        writer = csv.writer(fd)
        writer.writerow(data)


def _file_number_padding(index: int) -> str:
    
    if index < 10:
        return "000" + str(index)
    elif index < 100:
        return "00" + str(index)
    elif index < 1000:
        return "0" + str(index)
    else:
        return str(index)


if __name__ == "__main__":
    import time
    # import usb.core
    # import usb.util

    dc_power = Tenma_72_2535_manage()
    multimeter = Tenma_72_7730A_manage(0x1400)
    multimeter.start()
    logging = Logger()
    logging.set_column_width([40, 10, 10, 10, 10])

    dc_power.set_current(60)
    dc_power.power('ON')

    try:
        for index, voltage_step in enumerate(range(10, 311, 10)):
            test_report = []
            sentence = f'- Test n°{index} with voltage_step = {voltage_step} -'
            frame = '-' * len(sentence)
            print('\n\t', frame)
            print('\t', sentence)
            print('\t', frame, '\n')
            for time_after_set_voltage in range(10, 500, 30):
                # test init
                delta = []
                dc_power.set_voltage(2800)
                time.sleep(.5)
                for voltage in range(2800, 3501, voltage_step):
                    dc_power.set_voltage(voltage)
                    time.sleep(time_after_set_voltage / 1000)
                    measurement = int(multimeter.get_measurement())
                    delta.append(voltage / 400 - measurement)
                delta_mean_value = sum(delta)/len(delta)
                strange_value = [strange_value for strange_value in delta \
                        if \
                            abs(strange_value) > abs(delta_mean_value) * 1.2 \
                            or abs(strange_value) < abs(delta_mean_value) * 0.8 \
                        ]
                print(
                    f'{time_after_set_voltage}\t'
                    f'{delta_mean_value:.1f}\t'
                    f'{min(delta)}\t'
                    f'{max(delta)}\t'
                    f'Number of measurement: {len(delta)}\t'
                    f'{strange_value}\n'
                    )
                test_report.append([
                    time_after_set_voltage,
                    f'{delta_mean_value:.1f}',
                    min(delta),
                    max(delta),
                    strange_value])

            logging.add_lines_to_logging_file([''])
            logging.add_lines_to_logging_file([sentence])

            data = ["time_after_set_voltage (ms):"]
            data.extend([x[0] for x in test_report])
            data.extend(['Test OK'])
            logging.add_lines_to_logging_file(data)

            data = ["moyenne (mV):"]
            data.extend([x[1] for x in test_report])
            data.extend(['Test NOK'])
            logging.add_lines_to_logging_file(data)

            data = ["minimum (mV):"]
            data.extend([x[2] for x in test_report])
            data.extend(['Test OK'])
            logging.add_lines_to_logging_file(data)

            data = ["maximum (mV):"]
            data.extend([x[3] for x in test_report])
            data.extend(['Test NOK'])
            logging.add_lines_to_logging_file(data)

            data = ["valeur atypique:"]
            data.extend([x[4] for x in test_report])
            data.extend(['Test OK'])
            logging.add_lines_to_logging_file(data)

    except Exception as err:
                    print()
                    print(err)
                    print(err.__class__)
                    print(err.__doc__)
                    print(err.__dict__)
                    print()
                    logging.add_lines_to_logging_file([''])
                    logging.add_lines_to_logging_file([f'{err}'])
                    logging.add_lines_to_logging_file([f'{err.__class__}'])
                    logging.add_lines_to_logging_file([f'{err.__doc__}'])
                    logging.add_lines_to_logging_file([f'{err.__dict__}'])
                    logging.add_lines_to_logging_file([''])

    logging.stop_logging(f'Test {index} with voltage_step = {voltage_step}')
    dc_power.power('OFF')
    dc_power.disconnect()
    multimeter.kill()
    print('\tTest end.')
