#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils.summary_downloader import SummaryDownloader

if __name__ == '__main__':

    # setting target dir and time interval of interest
    tgt_dir = r"D:\nhl\official_and_json\2016-17"
    tgt_dir = r"d:\tmp\test"

    date = "2017/05/01"
    to_date = "2017/05/01"

    downloader = SummaryDownloader(tgt_dir, date, to_date, workers=8)
    downloader.run()
