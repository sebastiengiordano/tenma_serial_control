from os.path import dirname, join as os_path_join, exists, isfile
from os import listdir, makedirs, remove

import csv
from datetime import date

from xlsxwriter.workbook import Workbook


class Logger:
    '''Logger which create an ".xlsx" file which could be set with:

    Parameters:
        logging_name in order to create a file with the following format:
            TodayDate_logging_name_xxxx.xlsx (xxxx is interger)

        logging_folder relative path from logger.py folder path
        where create the log files
        (default: create "logging" folder in project root)

        columns_width in order to manage the width of each column
        (default: not column width modification)
            [40, 10]  ->  set the first colum to 40, the second to 10...

    Functions:
        add_lines_to_logging_file(list):
            each list's items are respectively write in columns of a new row

        stop_logging(sheet_name):
            when all needed data are stored, create the xlsx file
            with a sheet named 'sheet_name'
            (default: default excel file sheet name)

        set_logging_name(logging_name):
            in order to change the logging file name
            after Logger instantiation

        set_column_width(columns_width):
            in order to change excel sheet columns width
            after Logger instantiation
    '''

    def __init__(self,
                 logging_name='multimeter_Measurements',
                 logging_folder="../../logging",
                 columns_width=[]):
        self._logging_folder = logging_folder
        self._logging_logging_name = '_' + logging_name + '_'
        self._set_logging_folder()
        self._generate_logging_file_path()
        self.set_column_width(columns_width)

    def add_lines_to_logging_file(self, data: list):
        with open(
                self._logging_file_path,
                'a',
                newline='',
                encoding='utf8') as file:
            writer = csv.writer(file)
            writer.writerow(data)

    def stop_logging(self, sheet_name=None):
        '''After logging, convert csv to xlsx'''

        csvfile = self._logging_file_path
        # Create Workbook with worksheet named 'sheet_name'
        self._workbook = Workbook(csvfile[:-4] + '.xlsx')
        worksheet = self._workbook.add_worksheet(name=sheet_name)
        # Set cells format
        cell_format = self._set_cell_format()
        cell_format_ok = self._set_cell_format('green')
        cell_format_nok = self._set_cell_format('red')
        # Update column width
        for colum_index, width in enumerate(self._columns_width):
            worksheet.set_column(colum_index, colum_index, width)
        # Check if csv file has been created
        if not exists(csvfile):
            return
        # Write csv in xlsx
        with open(csvfile, 'rt', encoding='utf8') as file:
            reader = csv.reader(file)
            for r, row in enumerate(reader):
                for c, col in enumerate(row):
                    if col == 'Test OK':
                        choice_format = cell_format_ok
                    elif col == 'Test NOK' or col == 'Exception occurs':
                        choice_format = cell_format_nok
                    else:
                        choice_format = cell_format
                    worksheet.write(r, c, col, choice_format)
        self._workbook.close()
        # Delete temporary csv file
        remove(csvfile)
        # Update logging file's name
        self._generate_logging_file_path()

    def set_logging_name(self, logging_name: str):
        self._logging_logging_name = '_' + logging_name + '_'
        self._generate_logging_file_path()

    def set_column_width(self, columns_width: list = []):
        self._columns_width = columns_width

    def _set_cell_format(self, bg_color: str = ''):
        cell_format = self._workbook.add_format()
        cell_format.set_align('right')
        cell_format.set_align('vcenter')
        cell_format.set_indent(1)
        if not bg_color == '':
            cell_format.set_bg_color(bg_color)
        return cell_format

    def _files_in_folder(self, folder_path: str) -> list:
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
                files_in_subfolder = self._files_in_folder(file_or_dir_path)
                # Add relative path from folder_path
                for index, file in enumerate(files_in_subfolder.copy()):
                    files_in_subfolder[index] = file_or_dir + "/" + file
                # Add this files to the files list
                files_in_folder_path += files_in_subfolder
        return files_in_folder_path

    def _set_logging_folder(self):
        module_dir = dirname(__file__)
        logging_folder_path = os_path_join(
            module_dir,
            self._logging_folder)
        self._check_folder_exist_or_create(logging_folder_path)
        self._logging_folder_path = logging_folder_path

    def _get_logging_files_list(self):
        logging_files_list = self._files_in_folder(
            self._logging_folder_path)
        return logging_files_list

    def _generate_logging_file_path(self) -> None:
        '''Generate a new default logging file path'''
        logging_files_list = self._get_logging_files_list()
        today = date.today()
        today_in_str = (
            str(today.year) + "_"
            + str(today.month) + "_"
            + str(today.day)
            )
        for i in range(10000):
            file_name = (
                today_in_str
                + self._logging_logging_name
                + self._file_number_padding(i)
                )
            file_name_csv = file_name + ".csv"
            file_name_xlsx = file_name + ".xlsx"
            if (
                    file_name_csv not in logging_files_list
                    and
                    file_name_xlsx not in logging_files_list):
                self._logging_file_path = os_path_join(
                    self._logging_folder_path,
                    file_name_csv)
                break

    def _file_number_padding(self, index: int) -> str:
        if index < 10:
            return "000" + str(index)
        elif index < 100:
            return "00" + str(index)
        elif index < 1000:
            return "0" + str(index)
        else:
            return str(index)

    def _check_folder_exist_or_create(self, dir: str):
        '''
        From an absolute path, create the folder if it doesn't already exist
        '''
        # Check if this folder exist
        if not exists(dir):
            # Created the folders
            makedirs(dir)
