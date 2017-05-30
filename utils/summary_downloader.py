#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

import requests
from dateutil.parser import parse
from dateutil.rrule import rrule, DAILY

from multi_downloader import MultiFileDownloader


class SummaryDownloader(MultiFileDownloader):

    # base url for official schedule json page
    SCHEDULE_URL_BASE = "http://statsapi.web.nhl.com/api/v1/schedule"
    # url template for official json gamefeed page
    JSON_GAME_FEED_URL_TEMPLATE = (
        "http://statsapi.web.nhl.com/api/v1/game/%s/feed/live")
    # url parameter for json scoreboard page
    LINESCORE_CONTENT_KEY = "schedule.linescore"

    # defining necessary url prefixes
    NHL_PREFIX = r"http://www.nhl.com"
    # url prefix for html game reports
    HTML_REPORT_PREFIX = "".join((NHL_PREFIX, r"/scores/htmlreports/"))

    # defining valid game and report types
    REPORT_TYPES = ['GS', 'ES', 'FC', 'PL', 'TV', 'TH', 'RO', 'SS', 'SO']
    GAME_TYPES = ['P', 'R']

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
        # retrieving current date8
        self.curr_date = self.game_dates.pop(0)
        # retrieving current season
        self.season = (
            self.curr_date.year if
            self.curr_date.month > 6 else
            self.curr_date.year - 1)
        # preparing formatted date string as necessary for scoreboard retrieval
        fmt_date = "%d-%02d-%02d" % (
            self.curr_date.year, self.curr_date.month, self.curr_date.day)

        # retrieving schedule for current date in json format
        req = requests.get(
            self.SCHEDULE_URL_BASE, params={
                'startDate': fmt_date,
                'endDate': fmt_date,
                'expand': self.LINESCORE_CONTENT_KEY
            }
        )
        json_scoreboard = json.loads(req.text)
        self.files_to_download = self.get_files_to_download_from_scoreboard(
            json_scoreboard)

    def get_files_to_download_from_scoreboard(self, json_scoreboard):
        """
        Gets downloadable files from JSON scoreboard page.
        """
        files_to_download = list()
        for date in json_scoreboard['dates']:
            for game in date['games']:
                season = game['season']
                full_game_id = game['gamePk']
                game_type = game['gameType']
                game_id = str(full_game_id)[4:]

                # skipping game unless it's a regular season or playoff game
                if game_type not in self.GAME_TYPES:
                    continue
                for rt in self.REPORT_TYPES:
                    # only adding shootout report to files to be downloaded
                    # if the current game has had a shootout
                    if rt == 'SO' and not game['linescore']['hasShootout']:
                        continue
                    htmlreport_url = "".join((
                        self.HTML_REPORT_PREFIX,
                        season,
                        "/",
                        rt,
                        str(game_id),
                        ".HTM"))
                    files_to_download.append(htmlreport_url)
                feed_json_url = self.JSON_GAME_FEED_URL_TEMPLATE % str(
                    full_game_id)
                files_to_download.append(feed_json_url)

        return files_to_download


if __name__ == '__main__':

    date = "2017/04/01"
    to_date = "2017/04/01"

    d = SummaryDownloader(r"d:\tmp", date, to_date)
    d.find_files_to_download()
    for f in d.files_to_download:
        print(f)
