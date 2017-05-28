#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dateutil.parser import parse
from dateutil.relativedelta import DAILY
from dateutil.rrule import rrule


class SummaryDownloader():

    # base url for official schedule json page
    SCHEDULE_URL_BASE = "http://statsapi.web.nhl.com/api/v1/schedule"
    # url template for official json gamefeed page
    JSON_GAME_FEED_URL_TEMPLATE = (
        "http://statsapi.web.nhl.com/api/v1/game/%s/feed/live")

    MAX_DOWNLOAD_WORKERS = 8

    def __init__(self, tgt_dir, date, to_date='', threads=0):

        self.date = parse(date)
        if to_date:
            self.to_date = parse(to_date)
        else:
            self.to_date = self.date
        # preparing list of dates to download summary data for
        self.game_dates = list(
            rrule(DAILY, dtstart=self.date, until=self.to_date))
        print(self.game_dates)


if __name__ == '__main__':

    date = "1997/04/20"

    d = SummaryDownloader(r"d:\tmp", date)