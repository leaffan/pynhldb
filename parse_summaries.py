#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import argparse

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from parsers.main_parser import MainParser

FILENAME_REGEX = re.compile(R'^\d{4}\-\d{2}\-\d{2}$')

if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Parse previously downloaded NHL game summary reports.')
    parser.add_argument(
        '-d', '--src_dir', dest='src_dir', required=True,
        metavar='summary data source directory',
        help="Source directory for downloaded NHL game summary reports")
    parser.add_argument(
        '-f', '--from', dest='from_date', required=True,
        metavar='first date to parse summaries for',
        help="The first date summaries will be parsed for")
    parser.add_argument(
        '-t', '--to', dest='to_date', required=False,
        metavar='last date to parse summaries for',
        help="The last date summaries will be parsed for")
    # TODO: make it a list
    parser.add_argument(
        '-g', '--games', dest='tgt_game_ids', required=False,
        metavar='list of ids of games to parse', nargs='+',
        help="Game ids representing games to parse summaries")
    parser.add_argument(
        '--sequential', dest='sequential', required=False,
        action='store_true',
        help="Turn off multi-threaded parsing, turn on sequential parsing")
    parser.add_argument(
        '--exclude', dest='exclude', required=False, nargs='+',
        choices=['shifts', 'events'],
        help="Exclude the specified aspects from parsing")

    args = parser.parse_args()

    # setting source data directory from command line option
    src_dir = args.src_dir
    # setting time interval of interest from command line options
    from_date = parse(args.from_date).date()
    if args.to_date is not None:
        to_date = parse(args.to_date).date()
    else:
        to_date = from_date
    # setting game ids of interest from command line option
    if args.tgt_game_ids is not None:
        tgt_game_ids = sorted(args.tgt_game_ids)
    else:
        tgt_game_ids = None
    # toggling simultaneous/sequential parsing
    if args.sequential:
        sequential_parsing = True
    else:
        sequential_parsing = False

    print("+ Using source directory:", src_dir)
    print("+ Parsing from date:", from_date)
    print("+ Parsing to date:", to_date)
    print("+ Sequential parsing:", sequential_parsing)

    if to_date < from_date:
        print("+ Second date needs to be later than first date")
        sys.exit()

    # finding all dates between first and second specified date
    all_dates = set()
    all_dates.add(from_date)
    curr_date = from_date

    while curr_date != to_date:
        curr_date = curr_date + relativedelta(days=1)
        all_dates.add(curr_date)

    print("+ Parsing summaries for the following dates:")
    for date in sorted(all_dates):
        print("\t+ %s" % date)

    # TODO: find data source file for specified date(s)
    src_files = list()

    for root, dirs, files in os.walk(src_dir):
        for file in files:
            fname, ext = os.path.splitext(file)
            if re.search(FILENAME_REGEX, fname):
                if parse(fname).date() in all_dates:
                    print(os.path.join(root, file))
                    src_files.append(os.path.join(root, file))

    for file in src_files[:]:
        print("+ Using data source '%s'" % file)

        mp = MainParser(file, tgt_game_ids)
        if sequential_parsing:
            mp.parse_games_sequentially(args.exclude)
        else:
            mp.parse_games_simultaneously(args.exclude)
        mp.dispose()
