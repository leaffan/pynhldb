#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import uuid

from db.common import session_scope
# from db.player import Player
from db.player_game import PlayerGame

logger = logging.getLogger(__name__)


class RosterParser():

    def __init__(self, raw_data):
        # receiving structured raw data
        self.raw_data = raw_data
        # setting up dictionary for team roster data (from parsed document)
        self.roster_data = dict()
        # setting up dictionary for team rosters
        self.rosters = dict()

    def create_roster(self, game, teams):
        """
        Retrieves players rosters for specified game and teams.
        """
        # loading raw data
        self.load_data()

        for key in sorted(self.roster_data.keys(), reverse=True):
            curr_team = teams[key]
            self.rosters[key] = dict()
            print("\t+ Roster for %s (%s team):" % (curr_team, key))
            for roster_line in self.roster_data[key]:
                # retrieving number and player id
                # no = int(roster_line[0])

                pg_dict = dict()
                pg_dict['goals'] = int(roster_line[3])
                pg_dict['assists'] = int(roster_line[4])
                pg_dict['points'] = int(roster_line[5])
                pg_dict['pim'] = int(roster_line[8])

                plr_game_id = uuid.uuid4().urn
                plr_id = roster_line[-1]
                pg = PlayerGame(
                    plr_game_id, game.game_id,
                    curr_team.team_id, plr_id, pg_dict)
                print(pg, pg.player_game_id)

                with session_scope() as session:
                    session.add(pg)
                    session.commit()

                # plr = Player.find_by_id(plr_id)
        #         # retrieving name and prename from data line
        #         name, prename = roster_line[2].split(", ", 2)

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
            # appending player's nhl id
            for t, c in zip(trs, contents):
                c.append(int(t.xpath("td/span/@nhl_id")[0]))
            # setting roster data to retrieved contents
            self.roster_data[key] = contents
