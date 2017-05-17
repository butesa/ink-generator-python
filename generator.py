#! /usr/bin/python
# coding=utf-8

#   Generator-Python - a Inkscape extension to generate end-use files
#   from a model
#   Copyright (C) 2017 Johannes Matschke
#   Based on the Generator extension by Aurélio A. Heckert
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   Version 1.0

import sys
import os
import subprocess
import platform
import distutils.spawn
import tempfile
import shutil
import argparse
import csv
import ctypes


class SimpleObject:
    pass


class MyArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # use "argument" instead of "--argument"
        message = message.replace(' --', ' ')
        Show_error_and_exit('Argument error', message)


def Is_executable(filename):
    return distutils.spawn.find_executable(filename) is not None


if platform.system() != 'Windows' and Is_executable('zenity'):
    class ProgressBar():
        def __init__(self, title, text):
            self.__title = title
            self.__text = text
            self.__active = False

        def __enter__(self):
            self.__devnull = open(os.devnull, 'w')
            self.__proc = subprocess.Popen(
                [
                    'zenity',
                    '--progress',
                    '--title={0}'.format(self.__title),
                    '--text={0}'.format(self.__text),
                    '--auto-close',
                    '--width=400'
                ], stdin=subprocess.PIPE, stdout=self.__devnull,
                stderr=self.__devnull)
            self.__active = True
            return self

        def __exit__(self, *args):
            if self.__active:
                self.__close()

        def Set_percent(self, p):
            if self.is_active:
                self.__proc.stdin.write(str(p) + '\n')

        @property
        def is_active(self):
            if self.__active and self.__proc.poll() is not None:
                self.__close()
            return self.__active

        def __close(self):
            if not self.__proc.stdin.closed:
                self.__proc.stdin.close()
            if not self.__devnull.closed:
                self.__devnull.close()
            self.__active = False
else:
    class ProgressBar():
        def __init__(self, title, text):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def Set_percent(self, p):
            pass

        @property
        def is_active(self):
            return True


if platform.system() == 'Windows':
    def Show_info(title, message):
        MB_ICONINFORMATION = 0x40
        ctypes.windll.user32.MessageBoxA(0, message, title, MB_ICONINFORMATION)

    def Show_question(title, message):
        MB_ICONQUESTION = 0x20
        MB_YESNO = 0x4
        IDYES = 6
        return ctypes.windll.user32.MessageBoxA(
            0, message, title, MB_ICONQUESTION | MB_YESNO) == IDYES

    def Show_error_and_exit(title, message):
        MB_ICONERROR = 0x10
        ctypes.windll.user32.MessageBoxA(0, message, title, MB_ICONERROR)
        sys.exit(1)

elif Is_executable('zenity'):
    def Show_info(title, message):
        Zenity('info', title, message)

    def Show_question(title, message):
        return Zenity('question', title, message) == 0

    def Show_error_and_exit(title, message):
        Zenity('error', title, message)
        sys.exit(1)

    def Zenity(mode, title, message):
        return Call_no_output(
            [
                'zenity',
                '--{0}'.format(mode),
                '--title={0}'.format(title),
                '--text={0}'.format(message)
            ])
else:
    def Show_info(title, message):
        pass

    def Show_question(title, message):
        return None

    def Show_error_and_exit(title, message):
        sys.stderr.write(title + '\n' + message + '\n')
        sys.exit(1)


def Get_command_line_arguments():
    parser = MyArgumentParser()
    parser.add_argument(
        '--vartype', choices=['COLUMN', 'NAME'], required=True, type=str.upper,
        help='How to refer to columns')
    parser.add_argument(
        '--extravars', default='',
        help='Extra textual values to be replaced')
    parser.add_argument(
        '--datafile', required=True, help='path of CSV data file')
    parser.add_argument(
        '--format',
        choices=['PDF', 'SVG', 'PS', 'EPS', 'PNG', 'JPG'],
        default='PDF', type=str.upper, help='Export format')
    parser.add_argument(
        '--dpi', default='90', help='DPI (for PNG and JPG)')
    parser.add_argument(
        '--output', required=True, help='Output pattern')
    parser.add_argument(
        '--preview', choices=['TRUE', 'FALSE'], default='FALSE', type=str.upper,
        help='Preview (only first page)')
    parser.add_argument(
        '--specialchars', choices=['TRUE', 'FALSE'], default='TRUE', type=str.upper,
        help='Handle special XML characters')
    parser.add_argument('infile', help='SVG input file')

    args = parser.parse_known_args()[0]
    return args


def Generate(replacements):
    template = globaldata.template
    destfile = globaldata.args.output

    for search, replace in replacements:
        template = template.replace(search, replace)
        destfile = destfile.replace(search, replace)

    tmp_svg = os.path.join(globaldata.tempdir, 'temp.svg')

    with open(tmp_svg, 'wb') as f:
        f.write(template)

    if globaldata.args.format == 'SVG':
        shutil.move(tmp_svg, destfile)
    elif globaldata.args.format == 'JPG':
        tmp_png = os.path.join(globaldata.tempdir, 'temp.png')
        Ink_render(tmp_svg, tmp_png, 'PNG')
        Png_to_jpg(tmp_png, destfile)
    else:
        Ink_render(tmp_svg, destfile, globaldata.args.format)

    return destfile


def Ink_render(infile, outfile, format):
    Call_or_die(
        [
            'inkscape',
            '--without-gui',
            '--export-{0}={1}'.format(
                format.lower(), outfile),
            '--export-dpi={0}'.format(globaldata.args.dpi),
            infile
        ],
        'Inkscape Converting Error')


def Png_to_jpg(pngfile, jpgfile):
    if platform.system() == 'Windows':
        Show_error_and_exit(
            'JPG Export', 'JPG Export is not available on Windows.')
    elif Is_executable('convert'):
        Call_or_die(
            [
                'convert',
                'PNG:' + pngfile,
                'JPG:' + jpgfile
            ],
            'ImageMagick Converting Error')
    else:
        Show_error_and_exit(
            'JPG export', 'JPG export is not available because '
            'Image Magick is not installed.')


def Prepare_data(data_old):
    data_new = []
    if len(globaldata.args.extravars) == 0:
        extra_value_info = []
    else:
        extra_value_info = \
            [x.split('=>', 2) for x in globaldata.args.extravars.split('|')]

    for row in data_old:
        row_new = []
        for key, value in row:
            if key == '':
                continue
            if globaldata.args.specialchars == 'TRUE':
                value = value.replace('&', '&amp;')
                value = value.replace('<', '&lt;')
                value = value.replace('>', '&gt;')
                value = value.replace('"', '&quot;')
                value = value.replace("'", '&apos;')
            row_new.append(('%VAR_'+key+'%', value))
            for search_replace in extra_value_info:
                if len(search_replace) != 2:
                    Show_error_and_exit(
                        'Extra vars error',
                        'There is something wrong with your extra vars '
                        'parameter')
                if search_replace[1] == key:
                    row_new.append((search_replace[0], value))
        data_new.append(row_new)

    return data_new


def Open_file_viewer(filename):
    if platform.system() == 'Windows':
        os.startfile(filename)
    elif Is_executable('xdg-open'):
        Call_no_output(['xdg-open', filename])
    else:
        Show_error_and_exit(
            'No preview', 'Preview is not available because '
            '"xdg-open" is not installed.')


def Call_no_output(args):
    with open(os.devnull, 'w') as devnull:
        return subprocess.call(args, stdout=devnull, stderr=devnull)


def Call_or_die(args, error_title):
    try:
        subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        Show_error_and_exit(error_title, error.output)


def Process_csv_file(csvfile):
    if globaldata.args.vartype == 'COLUMN':
        csvdata = [[(str(x), y) for x, y in enumerate(row, start=1)]
                   for row in csv.reader(csvfile)]
    else:
        csvdata = [row.items() for row in csv.DictReader(csvfile)]

    csvdata = Prepare_data(csvdata)

    count = sum(1 for i in csvdata)
    if count == 0:
        Show_error_and_exit(
            'Empty CSV file', 'There are no data sets in your CSV file.')

    if globaldata.args.preview == 'TRUE':
        for row in csvdata:
            varlist = '\n'.join(
                [key for key, value in row])
            Show_info(
                'Generator Variables',
                'The replaceable text, based on your configuration and on '
                'the CSV are:\n{0}'.format(varlist))

            new_file = Generate(row)
            Open_file_viewer(new_file)
            break
    else:  # no preview
        with ProgressBar('Generator', 'Generating...') as progress:
            for num, row in enumerate(csvdata, start=1):
                Generate(row)
                if not progress.is_active:
                    break
                progress.Set_percent(num * 100 / count)


try:
    globaldata = SimpleObject()
    globaldata.args = Get_command_line_arguments()
    globaldata.tempdir = tempfile.mkdtemp()

    if not os.path.isfile(globaldata.args.datafile):
        Show_error_and_exit(
            'File not found', 'The CSV file "{0}" does not '
            'exist.'.format(globaldata.args.datafile))

    if (not os.path.splitext(globaldata.args.output)[1][1:].upper() ==
            globaldata.args.format):
        if Show_question(
                'Output file extension',
                'Your output pattern has a file extension '
                'diferent from the export format.\n\nDo you want to '
                'add the file extension?'):
            globaldata.args.output += '.' + \
                globaldata.args.format.lower()

    outdir = os.path.dirname(globaldata.args.output)
    if outdir != '' and not os.path.exists(outdir):
        os.makedirs(outdir)

    with open(globaldata.args.infile, 'rb') as f:
        globaldata.template = f.read()

    with open(globaldata.args.datafile, 'rb') as csvfile:
        Process_csv_file(csvfile)

finally:
    shutil.rmtree(globaldata.tempdir)
