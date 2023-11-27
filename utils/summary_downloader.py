#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import hashlib
from urllib.parse import urlsplit

import requests
from dateutil.parser import parse
from dateutil.rrule import rrule, DAILY

from .multi_downloader import MultiFileDownloader
from .summary_data_injector import add_nhl_ids_to_content
from utils import adjust_html_response

BASE_URL = 'https://api-web.nhle.com'


class SummaryDownloader(MultiFileDownloader):

    # base url for official schedule json page
    SCHEDULE_URL_BASE = f"{BASE_URL}/v1/schedule"
    # url template for official json gamefeed page
    JSON_GAME_FEED_URL_TEMPLATE = f"{BASE_URL}/v1/gamecenter/%s/play-by-play"
    # JSON_SHIFT_CHART_URL_TEMPLATE = "http://www.nhl.com/stats/rest/shiftcharts?cayenneExp=gameId=%s"
    JSON_SHIFT_CHART_URL_TEMPLATE = "https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=%s"
    # url parameter for json scoreboard page
    LINESCORE_CONTENT_KEY = "schedule.linescore"

    # defining necessary url prefixes
    NHL_PREFIX = r"http://www.nhl.com"
    # url prefix for html game reports
    HTML_REPORT_PREFIX = "".join((NHL_PREFIX, r"/scores/htmlreports/"))

    # defining valid game and report types
    REPORT_TYPES = ['GS', 'ES', 'FC', 'PL', 'TV', 'TH', 'RO', 'SS', 'SO']
    GAME_TYPES = [2, 3]

    GAME_ID_PATTERN = R"\d{2}\d{4}"

    def __init__(self, tgt_dir, date, to_date='', zip_summaries=True, workers=0, cleanup=True, exclude=None):
        # constructing base class instance
        super().__init__(tgt_dir, zip_summaries, workers, cleanup)
        # parsing start date for summary retrieval
        self.date = parse(date)
        # retrieving end date for summary retrieval
        if to_date:
            self.to_date = parse(to_date)
        else:
            self.to_date = self.date
        # preparing list of dates to download summary data for
        self.game_dates = list(rrule(DAILY, dtstart=self.date, until=self.to_date))
        # storing datasets to be excluded from downloading
        self.exclude = list()
        if exclude is not None:
            self.exclude = exclude

        # preparing connection to dumped dictionary of modification timestamps
        self.mod_timestamp_src = os.path.join(tgt_dir, '_mod_timestamps.json')
        # loading dictionary of previously downloaded summaries (if available)
        if os.path.isfile(self.mod_timestamp_src):
            self.mod_timestamps = json.loads(open(self.mod_timestamp_src).read())
        else:
            self.mod_timestamps = dict()

    def get_tgt_dir(self):
        """
        Returns target directory according to current date.
        """
        return os.path.join(self.base_tgt_dir, self.current_date.strftime("%Y-%m"))

    def get_zip_name(self):
        """
        Returns file name of zipped downloads for current date.
        """
        return "%04d-%02d-%02d" % (self.current_date.year, self.current_date.month, self.current_date.day)

    def get_zip_path(self):
        """
        Returns path to file of zipped downloaded files for current date.
        """
        return os.path.join(self.get_tgt_dir(), ".".join((self.get_zip_name(), 'zip')))

    def find_files_to_download(self):
        """
        Identifies files to be downloaded.
        """
        # making sure that the list of files to download is empty
        self.files_to_download = list()
        # preparing formatted date string as necessary for scoreboard retrieval
        fmt_date = "%d-%02d-%02d" % (self.current_date.year, self.current_date.month, self.current_date.day)

        # retrieving schedule for current date in json format
        schedule_url = "/".join((self.SCHEDULE_URL_BASE, fmt_date))
        req = requests.get(schedule_url)
        json_scoreboard = json.loads(req.text)
        self.files_to_download = self.get_files_to_download_from_scoreboard(json_scoreboard)

    def get_files_to_download_from_scoreboard(self, json_scoreboard):
        """
        Gets downloadable files from JSON scoreboard page.
        """
        files_to_download = list()
        for game in json_scoreboard['gameWeek'][0]['games']:
            season = game['season']
            full_game_id = game['id']
            game_type = game['gameType']
            game_id = str(full_game_id)[4:]

            # skipping game unless it's a regular season or playoff game
            if game_type not in self.GAME_TYPES:
                continue
            # constructing urls to individual game report pages
            if 'html_reports' not in self.exclude:
                for rt in self.REPORT_TYPES:
                    # only adding shootout report to files to be downloaded
                    # if the current game ended in a shootout
                    # if rt == 'SO' and not game['linescore']['hasShootout']:
                    #     continue
                    htmlreport_url = "".join((self.HTML_REPORT_PREFIX, str(season), "/", rt, str(game_id), ".HTM"))
                    files_to_download.append((htmlreport_url, None))
            # setting upd json game feed url and adding it to list of
            # files to be downloaded
            if 'game_feed' not in self.exclude:
                feed_json_url = self.JSON_GAME_FEED_URL_TEMPLATE % str(full_game_id)
                files_to_download.append((feed_json_url, ".".join((game_id, "json"))))
            # setting upd json shift chart url and adding it to list of
            # files to be downloaded
            if 'shift_chart' not in self.exclude:
                chart_json_url = self.JSON_SHIFT_CHART_URL_TEMPLATE % str(full_game_id)
                files_to_download.append((chart_json_url, "".join((game_id, "_sc.json"))))

        return files_to_download

    def get_last_modification_timestamp(self, url, tgt_path):
        """
        Retrieves timestamp of last modification for specified url if data
        had been downloaded before to the given target location.
        """
        # determining whether data has been downloaded before by checking if
        # target file exists in file system or in a corresponding zip file
        if (
            os.path.isfile(tgt_path) or self.check_for_file(
                self.zip_path, os.path.basename(tgt_path))
        ):
            # if data has been downloaded before, retrieve last
            # modification timestamp
            if url in self.mod_timestamps and self.mod_timestamps[url]:
                return self.mod_timestamps[url]

        return ""

    def download_task(self, url, tgt_dir, tgt_file):
        """
        Represents a single downloading task.
        """
        # setting up target path
        if tgt_file is None:
            tgt_file = os.path.basename(urlsplit(url).path)
        tgt_path = os.path.join(tgt_dir, tgt_file)

        # downloading data according to actual content type
        if url.lower().endswith('.htm'):
            content = self.download_html_content(url, tgt_path)
            write_type = 'wb'
        else:
            content = self.download_json_content(url, tgt_path)
            write_type = 'w'

        if content:
            # writing downloaded content to target path
            open(tgt_path, write_type).write(content)
            return tgt_path

    def download_html_content(self, url, tgt_path):
        """
        Downloads html content from specified url.
        """
        # retrieving timestamp of last modification in case data has been
        # downloaded before
        mod_time_stamp = self.get_last_modification_timestamp(url, tgt_path)
        # print(url, tgt_path, mod_time_stamp)
        # import sys
        # sys.exit()

        # setting up http headers using modification time stamp
        headers = dict()
        # modifing headers in case we're looking for an update of already
        # downloaded data
        if mod_time_stamp:
            headers['If-Modified-Since'] = mod_time_stamp
        req = requests.get(url, headers=headers)

        # if server responds with code for no modification
        if req.status_code == 304:
            # TODO: proper logging
            sys.stdout.write(".")
            sys.stdout.flush()
            return
        elif req.status_code == 200:
            # TODO: proper logging
            sys.stdout.write("+")
            sys.stdout.flush()
            # updating modification timestamp in corresponding dictionary
            self.mod_timestamps[url] = req.headers.get('Last-Modified')
            # adjusting html data
            content = adjust_html_response(req)
            if "ES" in url:
                content = add_nhl_ids_to_content(url, content)

            return content

    def download_json_content(self, url, tgt_path):
        """
        Downloads JSON content from specified url.
        """
        if tgt_path.endswith('_sc.json'):
            return self.download_json_shift_chart(url, tgt_path)
        else:
            return self.download_json_game_feed(url, tgt_path)

    def download_json_game_feed(self, url, tgt_path):
        """
        Downloads JSON game feed data from specified url.
        """
        # retrieving MD5 hash of data from last download
        prev_data_hash = self.get_last_modification_timestamp(url, tgt_path)

        req = requests.get(url)

        if req.status_code == 200:
            json_data = req.json()
            data_hash = hashlib.md5(json.dumps(json_data).encode('utf-8')).hexdigest()
            # checking whether json data that is due to update an existing data
            # set contains any play information at all and bailing out if that
            # is not the case - by doing so we avoid overwriting existing
            # *good* with *bad* data
            play_data = json_data['plays']
            if not play_data:
                # logging.warning("No playdata found %s" % url)
                sys.stdout.write("x")
                sys.stdout.flush()
                return
            # comparing time stamp of last modification of json data with
            # previously saved timestamp
            if data_hash == prev_data_hash:
                sys.stdout.write(".")
                sys.stdout.flush()
                return
            else:
                sys.stdout.write("+")
                sys.stdout.flush()
                # updating data hash in corresponding dictionary
                self.mod_timestamps[url] = data_hash
            # returning json data as prettily formatted string
            return json.dumps(json_data, indent=2)

    def download_json_shift_chart(self, url, tgt_path):
        """
        Downloads JSON shift data from specified url.
        """
        # retrieving timestamp of last modification in case data has been
        # downloaded before
        existing_data_hash = self.get_last_modification_timestamp(url, tgt_path)

        req = requests.get(url)

        if req.status_code == 200:
            json_data = req.json()
            # calculating MD5 hash for downloaded data
            json_data_hash = hashlib.md5(json.dumps(json_data).encode('utf-8')).hexdigest()
            # comparing hashes of downloaded and already exising data
            if not existing_data_hash == json_data_hash:
                sys.stdout.write("+")
                sys.stdout.flush()
                self.mod_timestamps[url] = json_data_hash
                return json.dumps(json_data, indent=2)
            else:
                sys.stdout.write(".")
                sys.stdout.flush()

    def get_downloaded_game_ids(self):
        """
        Gets game ids of games that have been downloaded.
        """
        game_ids = set([
            m.group(0) for f in list(map(os.path.basename, self.downloaded_files)) for
            m in [re.search(self.GAME_ID_PATTERN, f)] if m])

        return game_ids

    def run(self):
        """
        Runs downloading process for all registered game dates.
        """
        for date in self.game_dates:
            self.current_date = date
            print("+ Downloading summaries for %s" % self.current_date.strftime("%A, %B %d, %Y"))
            self.find_files_to_download()
            self.zip_path = self.get_zip_path()
            self.download_files(self.get_tgt_dir())
            print()

            downloaded_game_ids = self.get_downloaded_game_ids()
            if downloaded_game_ids:
                print("Downloaded data for the following game IDs:")
                print(" ".join(sorted(list(downloaded_game_ids))))

            if self.zip_downloaded_files:
                self.zip_files(self.get_zip_name(), self.get_tgt_dir())

        json.dump(self.mod_timestamps, open(self.mod_timestamp_src, 'w'), indent=2, sort_keys=True)
