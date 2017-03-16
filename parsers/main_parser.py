#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from lxml import html

from utils.data_handler import DataHandler
from parsers.team_parser import TeamParser
from parsers.game_parser import GameParser
from parsers.roster_parser import RosterParser
from parsers.goalie_parser import GoalieParser
from parsers.shift_parser import ShiftParser
from parsers.event_parser import EventParser

logger = logging.getLogger(__name__)


class MainParser():
    # data prefixes for official html datasets:
    #   ES ... event summary
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
        """
        Parses raw structured data for single game to create datbase-ready
        objects.
        """
        # setting up dictionary for structured raw data
        self.raw_data[game_id] = dict()
        self.parsed_data[game_id] = dict()

        # parsing current basic game information and participating teams
        (
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['teams']
        ) = self.create_game_and_teams(game_id)
        # print(self.parsed_data[game_id]['game'])
        # print(self.parsed_data[game_id]['teams'].keys())

        # parsing players participating in current game
        self.parsed_data[game_id]['rosters'] = self.create_rosters(game_id)
        # print(self.parsed_data[game_id]['rosters'].keys())

        # parsing goalies participating in current game
        self.parsed_data[game_id]['goalies'] = self.create_goalies(game_id)
        # print(self.parsed_data[game_id]['goalies'].keys())

        # parsing player create_shifts
        self.parsed_data[game_id]['shifts'] = self.create_shifts(game_id)
        # print(self.parsed_data[game_id]['shifts'].keys())

        self.parsed_data[game_id]['events'] = self.create_events(game_id)

        # removing raw structured data from memory
        del self.raw_data[game_id]

    def create_events(self, game_id):
        """
        Retrieves in-game events.
        """
        # reading play-by-play data anew if necessary
        self.read_on_demand(game_id, 'PL')
        # setting up parser for event data
        ep = EventParser(self.raw_data[game_id]['PL'])
        # retrieving event information using previously retrieved game and
        # roster information
        ep.create_events(
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['rosters'])

    def create_game_and_teams(self, game_id):
        """
        Retrieves essential game and team information from structured raw data.
        """
        # reading game summary data anew if necessary
        self.read_on_demand(game_id, 'GS')
        # setting up parser for team data
        tp = TeamParser(self.raw_data[game_id]['GS'])
        # retrieving teams participating in current game
        teams = tp.create_teams()
        # setting up parser for game data
        # GS data prefix, i.e. game summary data is necessary as the parser
        # collects all periods a goal was scored in
        # this information is only retrievable from GS type summaries
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
        rosters = rp.create_roster(
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['teams'])

        return rosters

    def create_goalies(self, game_id):
        """
        Retrieves goaltender information from structured raw data.
        """
        # setting up parser for goalie games
        gp = GoalieParser(
            self.raw_data[game_id]['GS'],
            self.read_on_demand(game_id, 'SO'))
        # retrieving goalies participating in current game
        goalies = gp.create_goalies(
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['rosters'])

        return goalies

    def create_shifts(self, game_id):
        """
        Retrieves shift information.
        """
        # setting up dictionary container for shifts from both teams
        shifts = dict()
        # doing this for both road and home team
        for prefix in ['TV', 'TH']:
            # reading time-on-ice data anew if necessary
            self.read_on_demand(game_id, prefix)
            # setting up parser for shift data
            sp = ShiftParser(self.raw_data[game_id][prefix])
            # selecting home or road type corresponding to data prefix
            if prefix == 'TV':
                home_road_type = 'road'
            else:
                home_road_type = 'home'
            # retrieving shift information
            shifts[home_road_type] = sp.create_shifts(
                self.parsed_data[game_id]['game'],
                self.parsed_data[game_id]['rosters'][home_road_type])
        else:
            return shifts

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
