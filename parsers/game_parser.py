#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime, time, timedelta

from dateutil import parser

from db import create_or_update_db_item
from db.common import session_scope
from db.game import Game
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

    def __init__(self, game_id, raw_data, raw_so_data=None):
        self.game_id = game_id
        self.raw_data = raw_data
        self.raw_so_data = raw_so_data

    def create_game(self, teams):
        # loading and pre-processing raw data
        self.load_data()

        game_data = dict()

        # retrieving game date from raw data
        game_data['date'] = parser.parse(self.game_data[0]).date()
        # retrieving season for current game date
        game_data['season'] = retrieve_season(game_data['date'])
        # setting up full game id, containing season, game type
        # and partial game id
        game_data['game_id'] = int(
            "%d%s" % (game_data['season'], self.game_id))
        # retrieving game type from partial game id
        game_data['type'] = int(self.game_id[:2])
        # retrieving game attendance and venue
        (
            game_data['attendance'],
            game_data['venue']) = self.retrieve_game_attendance_venue()
        # retrieving game start and end time
        game_data['start'], game_data['end'] = self.retrieve_game_start_end(
            game_data['date'], game_data['type'])
        (
            game_data['overtime_game'],
            game_data['shootout_game'],
            so_winner
        ) = self.retrieve_overtime_shootout_information(game_data['type'])
        # retrieving last modification date of original data
        try:
            game_data['data_last_modified'] = parser.parse(
                self.raw_data.xpath("//p[@id='last_modified']/text()")[0])
        except:
            game_data['data_last_modified'] = None
        # retrieving informatioan about participating teams
        team_dict = self.link_game_with_teams(teams)
        # merging team and game information
        game_data = {**game_data, **team_dict}
        # creating new game
        game = Game(game_data)
        # trying to find game in database
        db_game = Game.find_by_id(game.game_id)
        # updating existing or creating new game item in database
        create_or_update_db_item(db_game, game)

        return Game.find_by_id(game.game_id)

    def link_game_with_teams(self, teams):
        """
        Adds team information to current game.
        """
        game_team_dict = dict()

        for key in ['home', 'road']:
            curr_team = teams[key]
            game_team_dict["%s_team" % key] = curr_team
            game_team_dict["%s_team_id" % key] = curr_team.team_id
            game_team_dict["%s_score" % key] = curr_team.score
            game_team_dict["%s_overall_game_count" % key] = curr_team.game_no
            game_team_dict["%s_game_count" % key] = curr_team.home_road_no
            game_team_dict[curr_team.orig_abbr] = curr_team

        return game_team_dict

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

    def retrieve_overtime_shootout_information(self, game_type):
        """
        Retrieves information whether current game ended in overtime or a
        shootout.
        """
        overtime_game = False
        shootout_game = False
        so_winner = None

        # retrieving all scoring summary table rows
        scoring_trs = self.raw_data.xpath(
            "//td[contains(text(), 'SCORING SUMMARY')]/ancestor::tr/" +
            "following-sibling::tr[1]/td/table/tr[contains(@class, 'Color')]")

        # retrieving all table cells with periods a goal was scored in
        score_periods_tds = [tr.xpath("td[2]/text()")[0] for tr in scoring_trs]

        # checking regular season game...
        if game_type == 2:
            # ...for a shootout goal
            if 'SO' in score_periods_tds:
                shootout_game = True
                overtime_game = True
            # ...for an overtime goal
            elif 'OT' in score_periods_tds:
                overtime_game = True

            # retrieve shootout winning team abbreviation
            if shootout_game:
                so_winner = [
                    tr.xpath("td[5]/text()")[0] for tr in scoring_trs][-1]
        # checking playoff game...
        elif game_type == 3:
            # ...for an overtime goal, e.g. if there was a goal scored
            # in a period later than the third
            if max([int(x) for x in score_periods_tds]) > 3:
                overtime_game = True

        return overtime_game, shootout_game, so_winner

    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        # finding content of html element with *GameInfo*-id
        game_data_str = self.raw_data.xpath(
            "//table[@id='GameInfo']/tr/td/text()")
        game_data_str = [re.sub("\s+", " ", s) for s in game_data_str]
        self.game_data = remove_null_strings(game_data_str)[-5:]
