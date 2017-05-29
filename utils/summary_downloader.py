#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dateutil.parser import parse
from dateutil.rrule import rrule, DAILY


class SummaryDownloader():

    # base url for official schedule json page
    SCHEDULE_URL_BASE = "http://statsapi.web.nhl.com/api/v1/schedule"
    # url template for official json gamefeed page
    JSON_GAME_FEED_URL_TEMPLATE = (
        "http://statsapi.web.nhl.com/api/v1/game/%s/feed/live")

    MAX_DOWNLOAD_WORKERS = 8

    def __init__(self, tgt_dir, date, to_date='', workers=0):

        # parsing start date for summary retrieval
        self.date = parse(date)
        # retrieving end date for summary retrieval
        if to_date:
            self.to_date = parse(to_date)
        else:
            self.to_date = self.date
        # preparing list of dates to download summary data for
        self.game_dates = list(
            rrule(DAILY, dtstart=self.date, until=self.to_date))

        if workers:
            self.MAX_DOWNLOAD_WORKERS = workers

    def find_files_to_download(self):
        """
        Identifies files to be downloaded.
        """
        # making sure that the list of files to download is empty
        self.files_to_download = list()


if __name__ == '__main__':

    date = "1997/04/20"
    to_date = "1998/01/31"

    d = SummaryDownloader(r"d:\tmp", date, to_date)
