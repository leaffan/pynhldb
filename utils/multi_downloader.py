#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base class to allow inheriting objects to download multiple files from remote
locations at once.
"""
import os
import sys
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)


class MultiFileDownloader():

    TMP_DIR = tempfile.gettempdir()

    def __init__(self, tgt_dir):
        if not os.path.isdir(tgt_dir):
            try:
                os.makedirs(tgt_dir)
            except:
                print("Couldn't create target directory '%s'..." % tgt_dir)
                sys.exit(1)
        self.tgt_dir = tgt_dir
        self.files_to_download = list()
        self.downloaded_files = list()
        self.rejected_urls = list()
        self.zip_downloaded_files = False

    def toggle_zipping(self, zip_downloaded_files):
        if zip_downloaded_files is True:
            self.zip_downloaded_files = True
        else:
            self.zip_downloaded_files = False

    def find_files_to_download(self):
        raise NotImplementedError

    def download_files(self, workers):

        tgt_dir = self.tgt_dir

        self.files_to_download = sorted(self.files_to_download)

        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers) as download_threads:
                tasks = {download_threads.submit(
                    self.download_task,
                    url, tgt_dir): url for url in self.files_to_download}
                for completed_task in as_completed(tasks):
                    try:
                        completed_task.result()
                    except Exception as e:
                        print()
                        print("Task generated an exception: %s" % e)
        else:
            for url in self.files_to_download:
                print("Downloading %s" % url)
                self.download_task(url, tgt_dir)

    def download_task(self, url, tgt_dir):
        req = requests.get(url)
        open(os.path.join(tgt_dir, os.path.basename(url)), 'w').write(req.text)


if __name__ == '__main__':

    tgt_dir = r"d:\tmp\test"
    files_down_download = [
        "http://www.nhl.com/scores/htmlreports/20162017/PL021030.HTM",
        "http://www.nhl.com/scores/htmlreports/20162017/GS021030.HTM",
        "http://www.nhl.com/scores/htmlreports/20162017/TV021030.HTM"
    ]

    mdf = MultiFileDownloader(tgt_dir)
    mdf.files_to_download = files_down_download
    mdf.download_files(3)

