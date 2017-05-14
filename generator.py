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


class SimpleObject:
    pass


class MyArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # use "argument" instead of "--argument"
        message = message.replace(' --', ' ')
        Die('Argument error', message)


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
        '--preview', choices=['TRUE', 'FALSE'], default='TRUE', type=str.upper,
        help='Preview (only first page)')
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
        Imagemagick_convert(tmp_png, 'JPG:' + destfile)
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


def Imagemagick_convert(filefrom, fileto):
    Call_or_die(
        [
            'convert',
            filefrom,
            fileto
        ],
        'ImageMagick Converting Error')


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
            row_new.append(('%VAR_'+key+'%', value))
            for search_replace in extra_value_info:
                if len(search_replace) != 2:
                    Die('Extra vars error', 'There is something wrong with '
                        'your extra vars parameter')
                if search_replace[1] == key:
                    row_new.append((search_replace[0], value))
        data_new.append(row_new)

    return data_new


def Open_file_viewer(filename):
    if platform.system() == 'Windows':
        Call_no_output([filename])
    elif Is_executable('xdg-open'):
        Call_no_output(['xdg-open', filename])
    else:
        Die('No preview', 'Preview is not available because "xdg-open" is not '
            'installed.')


def Is_executable(filename):
    return distutils.spawn.find_executable(filename) is not None


def Popen_no_output(args):
    return subprocess.Popen(
        args, stdin=subprocess.PIPE, stdout=globaldata.devnull,
        stderr=globaldata.devnull)


def Call_no_output(args):
    return subprocess.call(
        args, stdout=globaldata.devnull, stderr=globaldata.devnull)


def Call_or_die(args, error_title):
    try:
        subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        Die(error_title, error.output)


def Die(title, message):
    if globaldata.use_zenity:
        Call_no_output(
            [
                'zenity',
                '--error',
                '--title={0}'.format(title),
                '--text={0}'.format(message)
            ])
    else:
        sys.stderr.write(title + '\n' + message + '\n')
    sys.exit(1)


def Process_csv_file(csvfile):
    if globaldata.args.vartype == 'COLUMN':
        csvdata = [[(str(x), y) for x, y in enumerate(row, start=1)]
                   for row in csv.reader(csvfile)]
    else:
        csvdata = [row.items() for row in csv.DictReader(csvfile)]

    csvdata = Prepare_data(csvdata)

    count = sum(1 for i in csvdata)
    if count == 0:
        Die('Empty CSV file', 'There are no data sets in your CSV file.')

    if globaldata.args.preview == 'TRUE':
        for row in csvdata:
            if globaldata.use_zenity:
                varlist = '\n'.join(
                    [key for key, value in row])

                Call_no_output(
                    [
                        'zenity',
                        '--info',
                        '--title=Generator Variables',
                        '--text=The replaceable text, based on your '
                        'configuration and on the CSV '
                        'are:\n{0}'.format(varlist)
                    ])

            new_file = Generate(row)
            Open_file_viewer(new_file)
            break
    else:  # no preview
        if globaldata.use_zenity:
            zenity = Popen_no_output(
                [
                    'zenity',
                    '--progress',
                    '--title=Generator',
                    '--text=Generating...',
                    '--auto-close',
                    '--width=400'
                ])

            for num, row in enumerate(csvdata, start=1):
                Generate(row)
                if zenity.poll() is not None:
                    break
                zenity.stdin.write(str(num * 100 / count) + '\n')
            zenity.stdin.close()
        else:
            for num, row in enumerate(csvdata, start=1):
                Generate(row)


try:
    globaldata = SimpleObject()
    globaldata.use_zenity = Is_executable('zenity')
    globaldata.devnull = open(os.devnull, 'w')
    globaldata.args = Get_command_line_arguments()
    globaldata.tempdir = tempfile.mkdtemp()

    if not os.path.isfile(globaldata.args.datafile):
        Die('File not found', 'The CSV file "{0}" does not exist.'.format(
            globaldata.args.datafile))

    if (not os.path.splitext(globaldata.args.output)[1][1:].upper() ==
            globaldata.args.format) and globaldata.use_zenity:
        result = Call_no_output(
            [
                'zenity',
                '--question',
                '--title=Output file extension',
                '--text=Your output pattern has a file extension '
                'diferent from the export format.\n\nDo you want to '
                'add the file extension?'
            ])
        if result == 0:
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
    try:
        globaldata.devnull.close()
    except:
        pass

    try:
        shutil.rmtree(globaldata.tempdir)
    except:
        pass
