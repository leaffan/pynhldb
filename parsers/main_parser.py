#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from lxml import html

from utils.data_handler import DataHandler
from parsers.team_parser import TeamParser
from parsers.game_parser import GameParser
from parsers.roster_parser import RosterParser
from parsers.goalie_parser import GoalieParser

logger = logging.getLogger(__name__)


class MainParser():
    # data prefixes for official html datasets:
    #   ES ... event summary,
    #   FC ... faceoff comparison
    #   GS ... game summary
    #   PL ... play-by-play report
    #   RO ... roster report
    #   SS ... shot summary
    #   TH ... time-on-ice report home team
    #   TV ... time-on-ice report visiting team
    #   SO ... shootout report
    REPORT_PREFIXES = ['ES', 'FC', 'GS', 'PL', 'RO', 'SS', 'TH', 'TV', 'SO']

    def __init__(self, data_src):
        # setting source for parsable raw data
        self.data_src = data_src

        # raw data is organized in a dictionary using game ids as keys
        self.raw_data = dict()
        # parsed data in dictionary using game ids as keys
        self.parsed_data = dict()

        # setting up data handler for specified data source
        self.dh = DataHandler(self.data_src)
        # retrieving all game ids contained in data source
        self.game_ids = self.dh.find_games()

    def parse_single_game(self, game_id):
        self.raw_data[game_id] = dict()
        self.parsed_data[game_id] = dict()

        (
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['teams']
        ) = self.create_game_and_teams(game_id)

        print(self.parsed_data[game_id]['game'])

        self.parsed_data[game_id]['rosters'] = self.create_rosters(game_id)

        print(self.parsed_data[game_id]['rosters'])

        self.gop = GoalieParser(self.raw_data[game_id]['GS'])
        self.gop.create_goalies(
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['rosters'])

        # self.read_on_demand(game_id, "ES")
        # print(len(self.raw_data[game_id]), self.raw_data[game_id])
        # self.read_on_demand(game_id, "GS")
        # print(len(self.raw_data[game_id]), self.raw_data[game_id])
        # self.read_on_demand(game_id, "TV")
        # print(len(self.raw_data[game_id]), self.raw_data[game_id])
        # self.read_on_demand(game_id, "TH")
        # print(len(self.raw_data[game_id]), self.raw_data[game_id])
        # self.read_on_demand(game_id, "ES")
        # print(len(self.raw_data[game_id]), self.raw_data[game_id])

        # import time
        # time.sleep(2)

        # removing raw structured data from memory
        del self.raw_data[game_id]

    # TODO:  test with another prefix instead of 'ES' and check memory usage
    def create_game_and_teams(self, game_id):
        """
        Retrieves essential game and team information from structured raw data.
        """
        # reading data anew if necessary
        self.read_on_demand(game_id, 'GS')
        # setting up parser for team data
        tp = TeamParser(
            self.raw_data[game_id]['GS'])
        # retrieving teams participating in current game
        teams = tp.create_teams()
        # setting up parser for game data
        gp = GameParser(
            game_id,
            self.raw_data[game_id]['GS'],
            self.read_on_demand(game_id, 'SO'))
        # retrieving essential game information, i.e. venue, attendance, score
        # using previously parsed team information
        game = gp.create_game(teams)

        return game, teams

    def create_rosters(self, game_id):
        """
        Retrieves roster information from structured raw data.
        """
        # reading data anew if necessary
        self.read_on_demand(game_id, "ES")

        # setting up parser for roster data
        rp = RosterParser(self.raw_data[game_id]['ES'])
        # retrieving roster information using previously retrieved game and
        # team information
        game_rosters = rp.create_roster(
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['teams'])

        return game_rosters

    def read_on_demand(self, game_id, prefix):
        """
        Reads original HTML data into structured raw data.
        """
        # returning raw data registered in corresponding dictionary if it
        # already has been read previously
        if game_id in self.raw_data:
            if prefix in self.raw_data[game_id]:
                return self.raw_data[game_id][prefix]

        # retrieving original html data from data source
        orig_data = self.dh.get_game_data(game_id, prefix, True)

        if prefix not in orig_data:
            return

        # creating raw structured tree from original html data
        self.raw_data[game_id][prefix] = html.document_fromstring(
            orig_data[prefix])

        return self.raw_data[game_id][prefix]
