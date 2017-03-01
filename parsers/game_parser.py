#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re

from dateutil import parser

from utils import remove_null_strings, retrieve_season

logger = logging.getLogger(__name__)


class GameParser():

    # defining time zone information
    TZINFO = {'CET':   3600, 'CEST': 7200,
              'EET':   7200, 'EETDST': 10800,
              'EDT': -14400, 'EST': -18000,
              'CDT': -18000, 'CST': -21600,
              'MDT': -21600, 'MST': -25200,
              'PDT': -25200, 'PST': -28800,
              'BST':   3600}

    # regular expression retrieve attendance figure
    ATTENDANCE_AT_VENUE_REGEX = re.compile("\s(@|at)\s")

    def __init__(self, game_id, raw_data, raw_so_data):
        self.game_id = game_id
        self.raw_data = raw_data
        self.raw_so_data = raw_so_data

    def create_game(self, teams):
        # loading and pre-processing raw data
        self.load_data()

        # retrieving game date from raw data
        game_date = parser.parse(self.game_data[0]).date()
        # retrieving season for current game date
        season = retrieve_season(game_date)
        # setting up full game id, containing season, game type
        # and partial game id
        full_game_id = "%d%s" % (season, self.game_id)

        attendance, venue = self.retrieve_game_attendance_venue()

    def retrieve_game_attendance_venue(self):
        """
        Retrieves attendance and venue information for current game.
        """
        # retrieving attendance and venue from string,
        # i.e. *Ass./Att. 21,273 @ Centre Bell*
        if any(s in self.game_data[1] for s in ['@', 'at']):
            attendance_venue = self.game_data[1].split(" ", 3)
            # print(attendance_venue)
            # attendance_venue = re.split(
            #     self.ATTENDANCE_AT_VENUE_REGEX, self.game_data[1])
            # print(attendance_venue)
        else:
            attendance_venue = self.game_data[1]

        try:
            attendance = int(attendance_venue[1].replace(",", ""))
        except:
            attendance = 0
        venue = attendance_venue[-1]

        return attendance, venue

    def load_data(self):
        """
        Loads raw data from html and pre-processes it.
        """
        # finding content of html element with *GameInfo*-id
        game_data_str = self.raw_data.xpath(
            "//table[@id='GameInfo']/tr/td/text()")
        game_data_str = [re.sub("\s+", " ", s) for s in game_data_str]
        self.game_data = remove_null_strings(game_data_str)[-5:]
