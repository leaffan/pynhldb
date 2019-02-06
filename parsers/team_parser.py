#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re

from db.team import Team
from utils import remove_null_strings

logger = logging.getLogger(__name__)

# TODO: use logger


class TeamParser():

    # regular expression to retrieve overall and home/road game counts
    GAME_COUNT_REGEX = re.compile(".+?(\d+).+?(\d+)")

    def __init__(self, raw_data):
        self.raw_data = raw_data
        # preparing dictionary containers for parsed team data
        self.team_data = dict()
        self.teams = dict()

    def create_teams(self):
        """
        Uses pre-processed data to retrieve teams participating in a game.
        """
        # loading and pre-processing raw data
        self.load_data()

        # usually for 'home' and 'road'
        for key in self.team_data:
            # receiving team data and getting rid of empty strings
            team_data = remove_null_strings(self.team_data[key])

            # retrieving score from last element
            score = int(team_data.pop())
            # retrieving overall game count and home/road game count from
            # second last element
            game_no, game_home_road_no = [
                int(n) for n in re.search(
                    self.GAME_COUNT_REGEX, team_data.pop()).group(1, 2)]
            # retrieving team name from third-last element
            name = team_data.pop()

            # finding team in database
            team = Team.find_by_name(name)
            # setting additional attributes
            team.game_no = game_no
            team.home_road_no = game_home_road_no
            team.score = score
            # adding team information to team dictionary
            self.teams[key] = team
            # using team abbreviation as key comes in handy later on
            self.teams[team.orig_abbr] = team
        else:
            return self.teams

    def create_teams_from_json(self):
        # TODO: create teams from JSON structure
        pass

    def load_data(self):
        """
        Loads raw data from html and pre-processes it.
        """
        # index variable for pre-2007 team and team score retrieval
        idx = 0

        # defining and itearting over combinations of table id used in html and
        # internal dictionary key
        for (html_id, dict_key) in [("Visitor", "road"), ("Home", "home")]:
            # team information retrieval from 2007 to present
            data_str = self.raw_data.xpath(
                "//table[@id='%s']/tr/td/text()" % html_id)
            # previously to 2007 this kind of information can only be retrieved
            # via a center tag inside a table data cell with a given width
            # as there are two teams per game sheet we need to track the
            # count via an index variable *idx*
            if not data_str:
                data_str = [s.strip() for s in self.raw_data.xpath(
                    "//td[@width=125][%d]/center" % (idx + 1) +
                    "/descendant-or-self::*/text()")]
            # team score retrieval from 2007 to present
            score_str = self.raw_data.xpath(
                "//table[@id='%s']/tr/td/table/tr/td/text()" % html_id)
            # previously to 2007 score information can only be retrieved
            # via the specified table width and font size values
            # as there are two scores per game sheet we need to track the
            # count via an index variable *idx*
            if not score_str:
                score_str = [self.raw_data.xpath(
                    "//td[@width=25]/font[@size=7]/text()")[idx].strip()]
            self.team_data[dict_key] = data_str + score_str
            idx += 1
