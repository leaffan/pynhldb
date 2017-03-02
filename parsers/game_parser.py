#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime, time, timedelta

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
        # print(full_game_id)

        # retrieving game type from partial game id
        game_type = int(self.game_id[:2])

        attendance, venue = self.retrieve_game_attendance_venue()
        # print("'%d' | '%s'" % (attendance, venue))

        start, end = self.retrieve_game_start_end(game_date, game_type)
        # print("start: %s | end : %s" % (start, end))

    def retrieve_game_attendance_venue(self):
        """
        Retrieves attendance and venue information for current game.
        """
        # retrieving combined attendance and venue from string,
        # i.e. *Ass./Att. 21,273 @ Centre Bell*
        if any(s in self.game_data[1] for s in ['@', 'at']):
            attendance_venue = self.game_data[1].split(" ", 3)
        else:
            attendance_venue = self.game_data[1].split(" ")

        # trying to convert attendance string into integer value
        try:
            attendance = int(attendance_venue[1].replace(",", ""))
        except:
            logger.warn(
                "+ Unable to convert '%s' to integer" % attendance_venue[1] +
                " attendance value")
            attendance = 0

        # retrieving venue from last element of string split above
        venue = attendance_venue[-1]

        return attendance, venue

    def retrieve_game_start_end(self, game_date, game_type):
        """
        Retrieves start and end timestamp for current game.
        """
        # retrieving start and end time strings from origina,
        # e.g. *Debut/Start 7:46 EDT; Fin/End 10:03 EDT*
        start_end = self.game_data[2].split(";")

        # retrieving raw start time and time zone
        start_time, start_timezone = start_end[0].split()[1:]
        # usually games start after noon
        start_time_suffix = "PM"
        # games may start before noon, but only in the 11th hour
        if int(start_time.split(":")[0]) in [11]:
            start_time_suffix = "AM"
        # turning raw start time, time zone and time suffix into timestamp
        start_time_stamp = parser.parse(
            u" ".join((start_time, start_timezone, start_time_suffix)),
            tzinfos=self.TZINFO)
        # combining game date and time stamp into full start time stamp
        start_date_time_stamp = datetime.combine(
            game_date, time(
                start_time_stamp.hour, start_time_stamp.minute,
                start_time_stamp.second, start_time_stamp.microsecond,
                start_time_stamp.tzinfo))

        # retrieving raw end time and time zone
        end_time, end_timezone = start_end[1].split()[1:]
        # usually games end after noon on the same day they started
        end_time_suffix = "PM"
        end_date = game_date
        # only playoff games may end after midnight
        if int(start_time.split(":")[0]) != 12:
            if int(end_time.split(":")[0]) < int(start_time.split(":")[0]):
                if game_type == 3:
                    print(start_end)
                    end_time_suffix = "AM"
                    end_date = game_date + timedelta(days=1)

        # turning raw end time, time zone and time suffix into timestamp
        end_time_stamp = parser.parse(
            u" ".join((end_time, end_timezone, end_time_suffix)),
            tzinfos=self.TZINFO)
        # combining game date and time stamp into full end time stamp
        end_date_time_stamp = datetime.combine(
            end_date, time(
                end_time_stamp.hour, end_time_stamp.minute,
                end_time_stamp.second, end_time_stamp.microsecond,
                end_time_stamp.tzinfo))

        return start_date_time_stamp, end_date_time_stamp

    def load_data(self):
        """
        Loads raw data from html and pre-processes it.
        """
        # finding content of html element with *GameInfo*-id
        game_data_str = self.raw_data.xpath(
            "//table[@id='GameInfo']/tr/td/text()")
        game_data_str = [re.sub("\s+", " ", s) for s in game_data_str]
        self.game_data = remove_null_strings(game_data_str)[-5:]
