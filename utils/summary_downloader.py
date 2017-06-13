#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
from urllib.parse import urlsplit

import requests
from lxml import html, etree
from dateutil.parser import parse
from dateutil.rrule import rrule, DAILY

from .multi_downloader import MultiFileDownloader
from .summary_data_injector import add_nhl_ids_to_content


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

    def __init__(
            self, tgt_dir, date, to_date='', zip_summaries=True, workers=0):
        # constructing base class instance
        super(self.__class__, self).__init__(tgt_dir, zip_summaries, workers)
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

        # TODO: rename modification timestamp container
        # preparing connection to dumped dictionary of modification timestamps
        self.mod_timestamp_src = os.path.join(tgt_dir, '_mod_timestamps.json')
        # loading dictionary of previously downloaded summaries (if available)
        if os.path.isfile(self.mod_timestamp_src):
            self.mod_timestamps = json.loads(
                open(self.mod_timestamp_src).read())
        else:
            self.mod_timestamps = dict()

        if workers:
            self.MAX_DOWNLOAD_WORKERS = workers

    def get_tgt_dir(self):
        """
        Returns target directory according to current date.
        """
        return os.path.join(self.tgt_dir, self.current_date.strftime("%Y-%m"))

    def get_zip_name(self):
        """
        Returns file name of zipped downloads for current date.
        """
        return "%04d-%02d-%02d" % (
            self.current_date.year,
            self.current_date.month,
            self.current_date.day)

    def get_zip_path(self):
        """
        Returns path to file of zipped downloaded files for current date.
        """
        return os.path.join(
            self.get_tgt_dir(), ".".join((self.get_zip_name(), 'zip')))

    def find_files_to_download(self):
        """
        Identifies files to be downloaded.
        """
        # making sure that the list of files to download is empty
        self.files_to_download = list()
        # retrieving current season
        self.season = (
            self.current_date.year if
            self.current_date.month > 6 else
            self.current_date.year - 1)
        # preparing formatted date string as necessary for scoreboard retrieval
        fmt_date = "%d-%02d-%02d" % (
            self.current_date.year,
            self.current_date.month,
            self.current_date.day)

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
                    files_to_download.append((htmlreport_url, None))
                feed_json_url = self.JSON_GAME_FEED_URL_TEMPLATE % str(
                    full_game_id)
                files_to_download.append(
                    (feed_json_url, ".".join((game_id, "json"))))

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
        else:
            content = self.download_json_content(url, tgt_path)

        if content:
            # writing downloaded content to target path
            open(tgt_path, 'w').write(content)
            # adding target path to list of downloaded files
            # self.downloaded_files.append(tgt_path)
            return tgt_path

    def download_html_content(self, url, tgt_path):
        """
        Downloads html content from specified url.
        """
        # retrieving timestamp of last modification in case data has been
        # downloaded before
        mod_time_stamp = self.get_last_modification_timestamp(url, tgt_path)

        # setting up http headers using modification time stamp
        headers = dict()
        # modifing headers in case we're looking for an update of already
        # downloaded data
        if mod_time_stamp:
            headers['If-Modified-Since'] = mod_time_stamp
        req = requests.get(url, headers=headers)

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
            content = self.adjust_html_response(req)
            if "ES" in url:
                content = add_nhl_ids_to_content(url, content)

            return content

    def download_json_content(self, url, tgt_path):
        """
        Downloads json content from specified url.
        """
        # retrieving timestamp of last modification in case data has been
        # downloaded before
        mod_time_stamp = self.get_last_modification_timestamp(url, tgt_path)
        # converting modification time stamp into actual datetime
        if mod_time_stamp:
            mod_time_stamp = parse(mod_time_stamp)

        req = requests.get(url)

        if req.status_code == 200:
            json_data = req.json()
            # retrieving time stamp for downloaded data
            act_time_stamp = parse(
                json_data['metaData']['timeStamp'].replace("_", " "))
            if act_time_stamp == mod_time_stamp:
                # TODO: proper logging
                sys.stdout.write(".")
                sys.stdout.flush()
                return
            else:
                # TODO: proper logging
                sys.stdout.write("+")
                sys.stdout.flush()
                # updating modification timestamp in corresponding dictionary
                self.mod_timestamps[url] = str(act_time_stamp)
                # returning json data as prettily formatted string
                return json.dumps(json_data, indent=2)

    def run(self):
        """
        Runs downloading process for all registered game dates.
        """
        for date in self.game_dates:
            self.current_date = date
            print(
                "+ Downloading summaries for %s" % self.current_date.strftime(
                    "%A, %B %d, %Y"))
            self.find_files_to_download()
            self.zip_path = self.get_zip_path()
            self.download_files(self.get_tgt_dir())
            print()
            self.zip_files(self.get_zip_name(), self.get_tgt_dir())

        json.dump(self.mod_timestamps, open(self.mod_timestamp_src, 'w'))

    def adjust_html_response(self, response):
        """
        Applies some modifications to the html source of the given HTTP
        response in order to alleviate later handling of the data.
        """
        # converting to document tree
        doc = html.document_fromstring(response.text)

        # stripping all script elements in order to remove javascripts
        etree.strip_elements(doc, "script")
        # stripping arbitraty xmlfile tag
        etree.strip_tags(doc, "xmlfile")

        # creating element to hold timestamp of last modification
        last_modified_element = etree.Element('p', id='last_modified')
        last_modified_element.text = response.headers.get('Last-Modified')

        # adding timestamp to document tree
        body = doc.xpath("body").pop(0)
        body.append(last_modified_element)

        # returning document tree dumped as string
        return etree.tostring(doc, method='html', encoding='unicode')
