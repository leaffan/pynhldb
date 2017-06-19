#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
from datetime import datetime

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from utils.summary_downloader import SummaryDownloader

if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download NHL game summary reports.')
    parser.add_argument(
        '-d', '--tgt_dir', dest='tgt_dir', required=True,
        metavar='download target directory',
        help="Target directories for downloads")
    parser.add_argument(
        '-f', '--from', dest='from_date', required=False,
        metavar='first date to download summaries for',
        help="The first date summaries will be downloaded for")
    parser.add_argument(
        '-t', '--to', dest='to_date', required=False,
        metavar='last date to download summaries for',
        help="The last date summaries will be downloaded for")

    args = parser.parse_args()

    # setting target dir and time interval of interest
    tgt_dir = args.tgt_dir
    from_date = args.from_date
    to_date = args.to_date

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