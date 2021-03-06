#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import logging
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

logger = logging.getLogger(__name__)


class DataHandler():

    GAME_ID_REGEX = re.compile('0(2|3)\d+')

    def __init__(self, dir_or_zip):
        self.src = dir_or_zip
        if os.path.isdir(dir_or_zip):
            self.dir = dir_or_zip
            self.src_type = 'dir'
        elif os.path.isfile(dir_or_zip):
            self.zip = ZipFile(dir_or_zip, 'r', compression=ZIP_DEFLATED)
            self.src_type = 'zip'
        else:
            print("%s is neither directory nor file..." % dir_or_zip)
            sys.exit(1)
        self.tmp_files = set()
        # retrieving all game ids from current directory or zip file
        self.find_games()

    def find_games(self):
        """
        Retrieves game ids of summary data files contained in current data
        source, i.e. zip file or directory.
        """
        # removing extension, retrieving last six characters of name and
        # checking whether remaining string is a valid game id for all
        # available summary data files
        self.game_ids = sorted(
            set(
                [os.path.splitext(e)[0][-6:] for e in self._get_contents()
                    if self.GAME_ID_REGEX.search(e) is not None]))
        return self.game_ids

    def get_game_data(self, game_id, prefix='ES'):
        """
        Retrieves game data, i.e. an html dataset, for a given game id
        and prefix. Either holds data in memory or stores it in a temporary
        file.
        """
        # checking whether this zip or dir contains this game
        if self.game_ids and game_id not in self.game_ids:
            return None

        game_data = dict()

        for item in self._get_contents():
            # checking item for game id
            if item.find(game_id) != -1:
                # checking item for data prefix
                if item.find(prefix) != -1:
                    abbr = item[0:2]
                    # retrieving game data from either
                    # a zipped file or
                    if self.src_type == 'zip':
                        game_data[abbr] = self._get_game_data_from_zip(item)
                    # a given directory
                    elif self.src_type == 'dir':
                        game_data[abbr] = self._get_game_data_from_dir(item)
        else:
            return game_data

    def _get_contents(self, file_type='HTM'):
        """
        Retrieves all available files from either a zip file or a directory.
        """
        if self.src_type == 'zip':
            return [s for s in self.zip.namelist() if os.path.splitext(
                s)[-1].lower().endswith(file_type.lower())]
        elif self.src_type == 'dir':
            return [s for s in os.listdir(self.dir) if os.path.splitext(
                s)[-1].lower().endswith(file_type.lower())]

    def get_game_json_data(self, nhl_game_id, data_type='game_feed'):
        """
        Retrieves JSON game feed or shift chart data for specified game id from
        data directory/zip file.
        """
        # checking whether current zip or dir contains game w/ soecified id
        if self.game_ids and nhl_game_id not in self.game_ids:
            logger.error("Game id {0} not found in contents of {1}".format(
                nhl_game_id, self.src))
            return None

        j_data = None

        # retrieving JSON data file for specified data type
        if data_type == 'game_feed':
            file_name_regex = re.compile("%s\.json" % nhl_game_id)
        elif data_type == 'shift_chart':
            file_name_regex = re.compile("%s_sc\.json" % nhl_game_id)

        for item in self._get_contents('.json'):
            if re.search(file_name_regex, item):
                if self.src_type == 'zip':
                    j_data = self._get_game_data_from_zip(item)
                elif self.src_type == 'dir':
                    j_data = self._get_game_data_from_dir(item)
                break

        return j_data

    def _get_game_data_from_zip(self, item):
        """
        Gets a game data item from a zip file.
        """
        # creating temporary file and returning location
        fd, tmp_name = tempfile.mkstemp('.nhl')
        fh = open(tmp_name, 'wb')
        fh.write(self.zip.read(item))
        os.close(fd)
        self.tmp_files.add(tmp_name)
        return tmp_name

    def _get_game_data_from_dir(self, item):
        """
        Gets a game data item from a directory.
        """
        # creating path
        path = os.path.join(self.dir, item)
        # returning file location
        return path

    def clear_temp_files(self):
        for f in self.tmp_files:
            try:
                os.unlink(f)
            except Exception as e:
                print("+ Unable to delete temporary file %s" % f)
                logger.warn("+ Unable to delete temporary file %s" % f)
        else:
            self.tmp_files.clear()
