#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging

from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def __init__(self, data_src, tgt_game_ids=None):
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
        # setting list of target game ids, i.e. games to actually parse
        if tgt_game_ids:
            self.tgt_game_ids = list(
                set(self.game_ids).intersection(tgt_game_ids))
        else:
            self.tgt_game_ids = self.game_ids

    def parse_games_sequentially(self, exclude=None):
        """
        Parses multiple games in a sequential manner, excludes the specified
        aspects (e.g. player shifts and/or game events) from processing.
        """
        for game_id in self.tgt_game_ids:
            self.parse_single_game(game_id, exclude)

    def parse_games_simultaneously(self, exclude=None, max_workers=8):
        """
        Parses multiple games in a parallel manner with the given maximum
        number of threads. Excludes the specified aspects (e.g. player shifts
        and/or game events) from processing.
        """
        with ThreadPoolExecutor(max_workers=max_workers) as threads:
            future_tasks = {
                threads.submit(
                    self.parse_single_game, game_id,
                    exclude): game_id for game_id in self.tgt_game_ids}
            for future in as_completed(future_tasks):
                try:
                    # TODO: think of something to do with the result here
                    data = future.result()
                    print(data)
                except Exception:
                    pass

    def parse_single_game(self, game_id, exclude):
        """
        Parses raw structured data for single game to create datbase-ready
        objects, excludes the specified aspects (e.g. player shifts and/or
        game events) from processing.
        """
        # creating empty list of aspects to exclude if necessary
        if exclude is None:
            exclude = list()

        # setting up dictionary for structured raw data
        self.raw_data[game_id] = dict()
        self.parsed_data[game_id] = dict()
        # parsing current basic game information and participating teams
        (
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['teams']
        ) = self.create_game_and_teams(game_id)
        print(self.parsed_data[game_id]['game'])
        # print(self.parsed_data[game_id]['teams'].keys())

        # parsing players participating in current game
        self.parsed_data[game_id]['rosters'] = self.create_rosters(game_id)
        # print(self.parsed_data[game_id]['rosters'].keys())

        # retrieving three star selections for game
        # this needs to be conducted at this position because roster
        # information is necessary to accomplish this task
        # raw game summary data has to be provided here, too
        # providing raw data within the scope of the game parser lead to
        # threading problems (for reason so far not understood)
        self.gp.retrieve_three_stars(
            self.parsed_data[game_id]['game'],
            self.parsed_data[game_id]['teams'],
            self.parsed_data[game_id]['rosters'],
            self.read_on_demand(game_id, 'GS'))

        # parsing goalies participating in current game
        self.parsed_data[game_id]['goalies'] = self.create_goalies(game_id)
        # print(self.parsed_data[game_id]['goalies'].keys())

        # parsing player shifts (if not optionally excluded from processing)
        if 'shifts' not in exclude:
            self.create_shifts(game_id)

        # parsing game events (if not optonally excluded from processing)
        if 'events' not in exclude:
            self.create_events(game_id)

        # removing raw structured data from memory
        del self.raw_data[game_id]

        return "+++ Finished parsing %s" % (
            self.parsed_data[game_id]['game'].short())

    def create_events(self, game_id):
        """
        Retrieves in-game events.
        """
        # reading play-by-play data anew if necessary
        self.read_on_demand(game_id, 'PL')
        # setting up parser for event data
        ep = EventParser(
            self.raw_data[game_id]['PL'],
            self.read_json_data(game_id),
            self.raw_data[game_id]['GS'])
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
        self.gp = GameParser(game_id, self.raw_data[game_id]['GS'])
        # retrieving essential game information, i.e. venue, attendance, score
        # using previously parsed team information
        game = self.gp.create_game(teams)
        # creating team/game item using raw game summary data and (if
        # available) raw shootout summary data
        self.gp.create_team_games(game, self.raw_data[game_id]['GS'], self.read_on_demand(game_id, 'SO'))

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
            self.parsed_data[game_id]['teams'],
            self.read_on_demand(game_id, 'RO'))

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
        # JSON shift data is less reliable than the HTML reports
        # that is why we're switching back here to the latter ones
        # which are available separately for both road and home team
        try:
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
                sp.create_shifts(
                    self.parsed_data[game_id]['game'], self.parsed_data[game_id]['rosters'][home_road_type])
        except Exception:
            print("Unable to retrieve shift information from HTML reports, trying JSON data instead")

            json_shift_data = self.read_json_data(game_id, data_type='shift_chart')
            if json_shift_data:
                sp = ShiftParser(json_shift_data)
                sp.create_shifts_from_json(
                    self.parsed_data[game_id]['game'],
                    self.parsed_data[game_id]['rosters'])

    def read_json_data(self, game_id, data_type='game_feed'):
        """
        Reads JSON game feed or shift chart data for game with specified id.
        """
        json_file = self.dh.get_game_json_data(game_id, data_type)

        if json_file is None:
            return

        return json.loads(open(json_file).read())

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
        orig_data = self.dh.get_game_data(game_id, prefix)

        if prefix not in orig_data:
            return

        # creating raw structured tree from original html data
        self.raw_data[game_id][prefix] = html.document_fromstring(open(
            orig_data[prefix]).read())

        return self.raw_data[game_id][prefix]

    def dispose(self):
        self.dh.clear_temp_files()
