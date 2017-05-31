#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils.summary_downloader import SummaryDownloader

if __name__ == '__main__':

    # setting target dir and time interval of interest
    tgt_dir = r"D:\nhl\official_and_json\2016-17"

    date = "May 20, 2017"
    to_date = "May 30, 2017"

    downloader = SummaryDownloader(tgt_dir, date, to_date)
    # downloader.run()
