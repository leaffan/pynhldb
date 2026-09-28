#!/usr/bin/env python

import argparse
import os
import re
import sys
from datetime import timedelta

from dateutil.parser import parse

from parsers.main_parser import MainParser
from utils import prepare_logging
from utils.pending_parse import PendingParseTracker

prepare_logging(log_types=['file', 'screen'])

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
    parser.add_argument(
        '--force', dest='force', required=False, action='store_true',
        help="Parse all games in the specified date range, ignoring " +
        "whether their raw data has changed since it was last parsed")

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
    all_dates = set([from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)])

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

    # tracks which games received changed raw data since they were last
    # parsed successfully, so that unchanged games can be skipped
    # _pending_parse.json lives next to _mod_timestamps.json in the download
    # target directory used for a given date's zip file, i.e. two directory
    # levels above it (base_tgt_dir/YYYY-MM/YYYY-MM-DD.zip) - this is not
    # necessarily src_dir itself, e.g. when src_dir covers multiple seasons
    # each with their own download target directory
    pending_trackers = dict()

    def get_pending_tracker(zip_file_path):
        base_tgt_dir = os.path.dirname(os.path.dirname(zip_file_path))
        if base_tgt_dir not in pending_trackers:
            pending_trackers[base_tgt_dir] = PendingParseTracker(base_tgt_dir)
        return pending_trackers[base_tgt_dir]

    for file in src_files[:]:
        fname, ext = os.path.splitext(os.path.basename(file))
        date_str = fname
        pending_tracker = get_pending_tracker(file)

        if args.force:
            # parsing everything found for this date, ignoring change status
            file_tgt_game_ids = tgt_game_ids
        else:
            pending_game_ids = pending_tracker.get_pending(date_str)
            if tgt_game_ids:
                # explicitly requested games are always parsed, in addition
                # to whatever else changed for this date
                file_tgt_game_ids = sorted(pending_game_ids.union(tgt_game_ids))
            else:
                file_tgt_game_ids = sorted(pending_game_ids)

            if not file_tgt_game_ids:
                print("+ No changed games to parse for %s, skipping" % date_str)
                continue

        print("+ Using data source '%s'" % file)

        mp = MainParser(file, file_tgt_game_ids)
        if sequential_parsing:
            mp.parse_games_sequentially(args.exclude)
        else:
            mp.parse_games_simultaneously(args.exclude)

        pending_tracker.mark_parsed(date_str, mp.succeeded_game_ids)
        mp.dispose()

    for pending_tracker in pending_trackers.values():
        pending_tracker.save()
