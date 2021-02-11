#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from lxml import etree

from utils import str_to_timedelta
from db import create_or_update_db_item
from db.team import Team
from db.shift import Shift

logger = logging.getLogger(__name__)


class ShiftParser():

    # partial xpath expression used for per player table row retrieval
    XPATH_EXPR = "sibling::tr[@class = 'oddColor' or @class = '	evenColor']"

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.shift_data = dict()

    def create_shifts(self, game, roster):
        """
        Creates shifts in specified game for given roster.
        """
        self.load_data()

        # retrieving team
        team_name = self.raw_data.xpath("//td[@class='teamHeading + border']/text()")[0]
        team = Team.find_by_name(team_name)

        for no in sorted(self.shift_data.keys()):
            # retrieving player with jersey number
            try:
                player = roster[no].get_player()
            except KeyError:
                # TODO: propper logging
                print(
                    "Unable to get player with number %d from team " % no +
                    "roster for %s. Skipping shift creation." % team)
                continue
            # retrieving all shifts for current player
            shifts = self.get_shifts_for_player(self.shift_data[no], player, game)

            # converting each single shift into a database item
            for shift_data_dict in shifts:
                shift_data_dict['no'] = no

                # setting up new shift item
                shift = Shift(game.game_id, team.team_id, player.player_id, shift_data_dict)

                # trying to find shift item in database
                db_shift = Shift.find(game.game_id, player.player_id, shift_data_dict['in_game_shift_cnt'])

                # creating new or updating existing shift item
                create_or_update_db_item(db_shift, shift)

    def create_shifts_from_json(self, game, rosters):
        """
        Creates shifts from JSON shift chart data.
        """
        # temporarily collecting all players' sweater numbers in a dictionary
        # using player_id as key
        rosters_by_player_id = dict()
        for home_road in rosters:
            for no in rosters[home_road]:
                rosters_by_player_id[rosters[home_road][no].player_id] = no

        for player_id in rosters_by_player_id:
            # retrieving and sorting raw shifts for current player
            raw_plr_shifts = list(filter(lambda sh: sh['playerId'] == player_id, self.raw_data['data']))
            raw_plr_shifts = sorted(raw_plr_shifts, key=lambda shf: (shf['period'], shf['startTime'], shf['endTime']))

            if not raw_plr_shifts:
                continue

            shf_cnt = 0
            shf_characteristics = set()

            # preparing container for extracted shift information
            prep_shifts = list()

            for raw_shift in raw_plr_shifts:
                # creating hashes
                # a) using period, start and end time of shift
                shf_hash = tuple([raw_shift['period'], raw_shift['startTime'], raw_shift['endTime']])
                # b) using period and start time of shift
                shf_start_hash = tuple([raw_shift['period'], raw_shift['startTime']])
                if shf_hash in shf_characteristics:
                    print("Shift for %d already registered: %s" % (player_id, str(shf_hash)))
                    continue
                if shf_start_hash in shf_characteristics:
                    print("Another shift for %d starting at %s in period %s already registered" % (
                        player_id, raw_shift['startTime'], raw_shift['period']))
                    continue
                shf_cnt += 1
                shf_characteristics.add(shf_hash)
                shf_characteristics.add(shf_start_hash)

                shift_data_dict = dict()
                # retrieving basic data
                shift_data_dict['player_id'] = player_id
                shift_data_dict['team_id'] = raw_shift['teamId']
                # retrieving sweater number by utilizing previously created dict
                shift_data_dict['no'] = rosters_by_player_id[player_id]
                # retrieving actual single shift data
                shift_data_dict['in_game_shift_cnt'] = raw_shift['shiftNumber']
                shift_data_dict['period'] = raw_shift['period']
                shift_data_dict['start'] = str_to_timedelta(raw_shift['startTime'])
                shift_data_dict['end'] = str_to_timedelta(raw_shift['endTime'])
                shift_data_dict['duration'] = str_to_timedelta(raw_shift['duration'])
                prep_shifts.append(shift_data_dict)

            # finally creating/updating shift information in database
            for prep_shift in prep_shifts:
                # setting up new shift item
                shift = Shift(game.game_id, prep_shift['team_id'], prep_shift['player_id'], prep_shift)

                # trying to find current shift item in database
                db_shift = Shift.find(game.game_id, prep_shift['player_id'], prep_shift['in_game_shift_cnt'])

                # creating new or updating existing shift item
                create_or_update_db_item(db_shift, shift)

    def get_shifts_for_player(self, shift_data_trs, player, game):
        """
        Gets all shifts in a game for a single player.
        """
        # setting up list of shifts
        shifts = list()
        for tr in shift_data_trs:
            # setting up data dictionary for single shift
            shift = dict()

            tokens = tr.xpath("td/text()")

            # retrieving in-game shift count
            shift['in_game_shift_cnt'] = int(tokens[0])
            # retrieving period for shift
            if tokens[1] == 'OT':
                shift['period'] = 4
            else:
                shift['period'] = int(tokens[1])
            # retrieving shift start time
            shift['start'] = str_to_timedelta(tokens[2].split("/")[0].strip())
            # retrieving shift end time
            try:
                shift['end'] = str_to_timedelta(tokens[3].split("/")[0].strip())
            # sometimes no end time is specified
            except Exception:
                logger.warning(
                    "Unable to extract time interval from raw" +
                    "data: %s (game id: %s, %s)" % (tokens[3], game.game_id, player.name))
                shift['end'] = None
            # retrieving shift duration
            shift['duration'] = str_to_timedelta(tokens[4])
            # if necessary calculating end time from start time and duration
            if shift['end'] is None:
                shift['end'] = shift['start'] + shift['duration']
            # appending single shift to list of all shifts
            shifts.append(shift)

        return shifts

    # TODO: optimize retrieval of table rows per player
    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        # retrieving all headings and spacers from html data, shift data for
        # each player is located between these two elements
        headings = self.raw_data.xpath("//td[@class='playerHeading + border']/parent::tr")
        spacers = self.raw_data.xpath("//td[@class='spacer + bborder + lborder + rborder']/parent::tr")

        # setting up tree to generate explicit xpath expressions for
        # considered elements
        tree = etree.ElementTree(self.raw_data)

        for h, s in zip(headings, spacers):
            # retrieving player's jersey number
            try:
                no = int(h.xpath("td/text()")[0].split()[0])
            except Exception:
                print("unable to get player number from shift table heading")
                continue
            # retrieving explicit xpath expressions for both
            # current heading and spacer
            ns1 = tree.getpath(h)
            ns2 = tree.getpath(s)
            # adjusting xpath expressions to include following and preceding
            # siblings with the specified class design
            ns1 = "%s/following-%s" % (ns1, self.XPATH_EXPR)
            ns2 = "%s/preceding-%s" % (ns2, self.XPATH_EXPR)
            # using the Kayessian method for node-set intersection to retrieve
            # all elements between the current header and spacer elements, see
            # http://is.gd/bXsKGH
            expr = "%s[count(.|%s) = count(%s)]" % (ns1, ns2, ns2)
            # applying expression to data
            shift_data = self.raw_data.xpath(expr)

            self.shift_data[no] = shift_data
