#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from datetime import datetime

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from utils import get_target_directory_from_config_file
from utils.summary_downloader import SummaryDownloader

if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download NHL game summary reports.')
    parser.add_argument(
        '-d', '--tgt_dir', dest='tgt_dir', required=False,
        metavar='download target directory',
        help="Target directory for downloads")
    parser.add_argument(
        '-f', '--from', dest='from_date', required=False,
        metavar='first date to download summaries for',
        help="The first date summaries will be downloaded for")
    parser.add_argument(
        '-t', '--to', dest='to_date', required=False,
        metavar='last date to download summaries for',
        help="The last date summaries will be downloaded for")

    args = parser.parse_args()

    # setting time interval of interest from command line options
    from_date = args.from_date
    to_date = args.to_date

    # setting target directory from command line options...
    if args.tgt_dir is not None:
        tgt_dir = args.tgt_dir
    # ...or from configuration file
    else:
        cfg_src = os.path.join(os.path.dirname(__file__), r"_config.ini")
        tgt_dir = get_target_directory_from_config_file(cfg_src, 'downloading')

    # bailing out if target directory doesn't exist
    if not os.path.isdir(tgt_dir):
        print("+ Download target directory '%s' does not exist" % tgt_dir)
        print("+ Update configuration or specify via -d/--tgt_dir option")
        sys.exit()

    # setting first date to download summaries for if not specified
    if from_date is None:
        # using previously downloaded files in target directory to retrieve
        # last date data have already been downloaded before
        all_dates = list()
        for root, dirs, files in os.walk(tgt_dir):
            for file in files:
                if file.lower().endswith(".zip") and file.lower()[0].isdigit():
                    try:
                        curr_date = parse(os.path.basename(file.split(".")[0]))
                        all_dates.append(curr_date)
                    except:
                        pass

        from_date = (sorted(all_dates)[-1] + relativedelta(days=1)).strftime(
            "%B %d, %Y")

    # setting last date to download summaries for...
    if to_date is None:
        # ...to same as first date to download summaries for if this one is set
        if args.from_date:
            to_date = from_date
        # ...to date before current one otherwise
        else:
            to_date = (datetime.now() + relativedelta(days=-1)).strftime(
                "%B %d, %Y")

    downloader = SummaryDownloader(tgt_dir, from_date, to_date, workers=8)
    downloader.run()
