#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base class to allow inheriting objects to download multiple files from remote
locations at once.
"""
import os
import time
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

logger = logging.getLogger(__name__)


class MultiFileDownloader():

    TMP_DIR = tempfile.gettempdir()
    WORKERS = 8

    def __init__(
            self, tgt_dir, zip_downloaded_files=True, workers=0, cleanup=True):
        if not os.path.isdir(tgt_dir):
            try:
                os.makedirs(tgt_dir)
            except:
                logger.warn(
                    "Couldn't create target directory '%s', using " % tgt_dir +
                    "system temporary directory %s instead" % self.TMP_DIR)
                tgt_dir = self.TMP_DIR
        self.base_tgt_dir = tgt_dir
        self.files_to_download = list()
        self.downloaded_files = list()
        self.cleanup = cleanup
        # self.rejected_urls = list()
        self.zip_downloaded_files = zip_downloaded_files

        if workers:
            self.workers = workers
        else:
            self.workers = self.WORKERS

    def toggle_zipping(self, zip_downloaded_files):
        if zip_downloaded_files is True:
            self.zip_downloaded_files = True
        else:
            self.zip_downloaded_files = False

    def find_files_to_download(self):
        """
        Base class function representing a solution to find downloadable files.
        """
        raise NotImplementedError

    def download_files(
            self, tgt_dir=None, files_to_download=None):

        # clearing list of downloaded files first
        self.downloaded_files = list()

        if tgt_dir is None:
            tgt_dir = self.base_tgt_dir
        if not os.path.isdir(tgt_dir):
            os.makedirs(tgt_dir)
        if files_to_download is None:
            files_to_download = self.files_to_download

        files_to_download = sorted(files_to_download)

        if self.workers > 1:
            with ThreadPoolExecutor(max_workers=self.workers) as dld_threads:
                tasks = {dld_threads.submit(
                    self.download_task,
                    url,
                    tgt_dir,
                    tgt_file): (
                        url, tgt_file) for url, tgt_file in files_to_download}
                for completed_task in as_completed(tasks):
                    try:
                        if completed_task.result():
                            self.downloaded_files.append(
                                completed_task.result())
                    except Exception as e:
                        print()
                        print("Task generated an exception: %s" % e)
        else:
            for url, tgt_file in files_to_download:
                result = self.download_task(url, tgt_dir, tgt_file)
                if result:
                    self.downloaded_files.append(result)

    def download_task(self, url, tgt_dir, tgt_file):
        """
        Base class function representing a single downloading task.
        """
        raise NotImplementedError

    def check_for_file(self, zip_path, file_name):
        """
        Checks whether the zip file specified by its path contains the given
        file name.
        """
        if not zip_path or not os.path.isfile(zip_path):
            return False

        zip = ZipFile(zip_path)

        if file_name in zip.namelist():
            return True
        else:
            return False

    def zip_files(self, zip_name, sub_dir=""):
        """
        Zips downloaded files to a zip file with the specified name.
        """
        # bailing out if no files were downloaded
        if len(self.downloaded_files) == 0:
            return

        # setting up zip file location
        zip_file = "".join((zip_name, ".zip"))
        zip_path = os.path.join(self.base_tgt_dir, sub_dir, zip_file)
        print("+ Zipping downloaded files to %s..." % zip_path)

        files_in_zip, files_in_zip_info = self.analyze_zip_file(zip_path)

        files_to_zip = self.prepare_zip_contents(
            files_in_zip, files_in_zip_info)

        self.create_new_zip_file(zip_path, files_to_zip, files_in_zip_info)

        if self.cleanup:
            self._clean_up_after_zip(files_in_zip, files_to_zip)

    def analyze_zip_file(self, zip_path):
        """
        Analyzes an already existing zip file at the specified location,
        retrieving file contents and date of last modification for each
        included file.
        """
        # creating list files contained by an already existing zip file
        files_in_zip = list()
        # creating dictionary with modification dates of files contained
        # by an already existing zip file
        files_in_zip_info = dict()

        # checking whether a zip file exists at the specified location
        if os.path.isfile(zip_path):
            existing_zip = ZipFile(zip_path)
            # extracting all contents to user's temporary directory
            existing_zip.extractall(self.TMP_DIR)
            # retrieving names of zipped files
            files_in_zip = existing_zip.namelist()
            # retrieving modification dates of each zipped file
            for f in files_in_zip:
                files_in_zip_info[f] = existing_zip.getinfo(f).date_time + (
                    0, 0, -1)
            existing_zip.close()

        return files_in_zip, files_in_zip_info

    def prepare_zip_contents(self, files_in_zip, files_in_zip_info):
        """
        Prepares contents of a newly to be created zip file by comparing
        existing contents with downloaded files.
        """
        # creating list of files to be put into new zip file, using files
        # from an already existing one as a base
        files_to_zip = files_in_zip

        for f in self.downloaded_files:
            # if one of the downloaded files has been found in existing zip...
            if os.path.basename(f) in files_in_zip:
                # removing old file from list of files to be zipped
                files_to_zip.remove(os.path.basename(f))
                # deleting modification date information for old file
                del files_in_zip_info[os.path.basename(f)]
                # deleting old file from hard disk
                os.unlink(os.path.join(self.TMP_DIR, os.path.basename(f)))
            # appending downloaded file to list of files to be zipped
            files_to_zip.append(f)

        # adjusting path of files to be zipped to include temporary directory
        files_to_zip = [
            os.path.join(self.TMP_DIR, f) if not os.path.isfile(
                f) else f for f in files_to_zip]

        return files_to_zip

    def create_new_zip_file(self, zip_path, files_to_zip, files_in_zip_info):
        """
        Creates a new zip file at specified location adding the files and using
        the file information specified.
        """
        # creating new zip file
        new_zip = ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED)

        for f in files_to_zip:
            # retrieving modification date, either ...
            if os.path.basename(f) in files_in_zip_info:
                # for an existing file
                date_time = time.localtime(
                    time.mktime(files_in_zip_info[os.path.basename(f)]))
            else:
                # for a downloaded file
                date_time = time.localtime(os.path.getmtime(f))
            # creating zip information
            info = ZipInfo(f, date_time=date_time)
            # setting compress type
            info.compress_type = ZIP_DEFLATED
            # setting name of zipped file
            info.filename = os.path.basename(f)
            # adding file to new zip file
            new_zip.writestr(info, open(f).read())

        new_zip.close()

    def _clean_up_after_zip(self, files_in_zip, files_to_zip):
        """
        Removes temporarily created files after zip file creation.
        """
        all_files = set(self.downloaded_files)
        all_files.update([os.path.join(self.TMP_DIR, f) for f in files_in_zip])
        all_files.update(files_to_zip)

        for f in all_files:
            try_delete_count = 0
            while try_delete_count < 5 and os.path.isfile(f):
                try:
                    try_delete_count += 1
                    os.unlink(f)
                except:
                    print(f)
                    # TODO: log
                    pass
