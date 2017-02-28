#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re


from utils import remove_null_strings

logger = logging.getLogger(__name__)


class GameParser():

    # defining time zone information
    TZINFO = {'CET':   3600, 'CEST':    7200,
              'EET':   7200, 'EETDST': 10800,
              'EDT': -14400, 'EST': -18000,
              'CDT': -18000, 'CST': -21600,
              'MDT': -21600, 'MST': -25200,
              'PDT': -25200, 'PST': -28800,
              'BST':   3600}

    # regular expression retrieve attendance figure
    ATTENDANCE_AT_VENUE_REGEX = re.compile("\s(@|at)\s")

    def __init__(self, raw_data, raw_so_data):
        self.raw_data = raw_data
        self.raw_so_data = raw_so_data

    def load_data(self):
        """
        Loads raw data from html and pre-processes it.
        """
        # finding content of html element with *GameInfo*-id
        game_data_str = self.raw_data.xpath(
            "//table[@id='GameInfo']/tr/td/text()")
        game_data_str = [re.sub("\s+", " ", s) for s in game_data_str]
        self.game_data = remove_null_strings(game_data_str)[-5:]
