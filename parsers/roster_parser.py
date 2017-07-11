#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from utils import str_to_timedelta
from db import create_or_update_db_item
from db.player_game import PlayerGame

logger = logging.getLogger(__name__)


class RosterParser():

    # event summary values and statistics for each player in roster in
    # exact the same order as in the original html table row
    PLAYER_GAME_ATTRS = [
        "no", "position", "name", "goals", "assists", "points", "plus_minus",
        "penalties", "pim", "toi_overall", "no_shifts", "avg_shift", "toi_pp",
        "toi_sh", "toi_ev", "shots_on_goal", "shots_blocked", "shots_missed",
        "hits", "giveaways", "takeaways", "blocks",
        "faceoffs_won", "faceoffs_lost",
    ]

    def __init__(self, raw_data):
        # receiving structured raw data
        self.raw_data = raw_data
        # setting up dictionary for team roster data (from parsed document)
        self.roster_data = dict()
        # setting up final dictionary for team rosters
        self.rosters = dict()

    def create_roster(self, game, teams):
        """
        Retrieves players rosters for specified game and teams.
        """
        # loading and pre-processing structred raw data
        self.load_data()

        for key in sorted(self.roster_data.keys(), reverse=True):
            curr_team = teams[key]
            self.rosters[key] = dict()
            for roster_line in self.roster_data[key]:
                plr_id = roster_line['plr_id']
                # TODO: check whether player exists in database
                # TODO: otherwise create one
                # setting up new player game item
                new_pgame = PlayerGame(
                    game.game_id, curr_team.team_id, plr_id, roster_line)
                # trying to find existing player game item in database
                db_pgame = PlayerGame.find(
                    new_pgame.game_id, new_pgame.player_id)
                # updating existing or creating new player game item
                create_or_update_db_item(db_pgame, new_pgame)
                # adding player game item to team roster dictionary for current
                # game using jersey number as key
                self.rosters[key][new_pgame.no] = PlayerGame.find(
                    new_pgame.game_id, new_pgame.player_id)
        else:
            return self.rosters

    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        # retrieving all table row elements that are located either above or
        # below a table row that spans the whole table width and separates
        # road and home team rosters
        self.roster_data['road'] = self.raw_data.xpath(
            "//tr/td[@colspan='25' or @colspan='22']/parent::*/" +
            "preceding-sibling::*")
        self.roster_data['home'] = self.raw_data.xpath(
            "//tr/td[@colspan='25' or @colspan='22']/parent::*/" +
            "following-sibling::*")

        # transforming table row elements into lists of data
        for key in ['road', 'home']:

            roster_list = list()

            trs = self.roster_data[key]
            # retaining only those rows that have a number in their first table
            # cell, i.e. represent a player
            trs = [tr for tr in trs if tr.xpath("td/text()")[0].isnumeric()]
            # retaining only those rows that contain more cells than a certain
            # threshold, thereby eliminating additional rows for goalies
            trs = [tr for tr in trs if len(tr) > 15]
            # retrieving text contents
            contents = [tr.xpath("td/text()") for tr in trs]
            # replacing null strings with zeros
            contents = [[
                s.replace('\xa0', '0') for s in item] for item in contents]

            # creating data dictionaries for each table row, e.g. player
            for tr, content in zip(trs, contents):
                content = [c for c in content if c.strip()]
                single_roster_line = dict()
                # adding player id to single roster line
                single_roster_line['plr_id'] = int(
                    tr.xpath("td/span/@nhl_id")[0])
                # retrieving values from table row contents
                for attr in self.PLAYER_GAME_ATTRS:
                    val = content[self.PLAYER_GAME_ATTRS.index(attr)]
                    # converting time-on-ice data and average shift length
                    # to timedelta intervals
                    if attr.startswith('toi') or attr.startswith('avg'):
                        val = str_to_timedelta(val)
                    # leaving position and name unchanged
                    elif attr in ('position', 'name'):
                        pass
                    # converting everything else into integers
                    else:
                        val = int(val)
                    single_roster_line[attr] = val
                # adding single roster line to all roster lines
                roster_list.append(single_roster_line)
            # setting roster data for current team type to retrieved contents
            self.roster_data[key] = roster_list
