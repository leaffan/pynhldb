#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from collections import defaultdict

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
        self.shifts = defaultdict(list)

    def create_shifts(self, game, roster):
        """
        Creates shifts in specified game for given roster.
        """
        self.load_data()

        # retrieving team
        team_name = self.raw_data.xpath(
            "//td[@class='teamHeading + border']/text()")[0]
        team = Team.find_by_name(team_name)

        for no in sorted(self.shift_data.keys()):
            # retrieving player with jersey number
            player = roster[no].get_player()
            # retrieving all shifts for current player
            shifts = self.get_shifts_for_player(self.shift_data[no], player)

            # converting each single shift into a database item
            for shift_data_dict in shifts:
                shift_data_dict['no'] = no

                # setting up new shift item
                shift = Shift(
                    game.game_id, team.team_id, player.player_id,
                    shift_data_dict)

                # trying to find shift item in database
                db_shift = Shift.find(
                    game.game_id, player.player_id,
                    shift_data_dict['in_game_shift_cnt'])

                # creating new or updating existing shift item
                create_or_update_db_item(db_shift, shift)

                self.shifts[no].append(
                    Shift.find(
                        shift.game_id, shift.player_id,
                        shift.in_game_shift_cnt))
        else:
            return self.shifts

    def get_shifts_for_player(self, shift_data_trs, player):
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
                shift['end'] = str_to_timedelta(
                    tokens[3].split("/")[0].strip())
            # sometimes no end time is specified
            except:
                logger.warning(
                    "Unable to extract time interval from raw" +
                    "data: %s (game id: %s, %s)" % (
                        tokens[3], self.game.game_id, player.name))
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
        headings = self.raw_data.xpath(
            "//td[@class='playerHeading + border']/parent::tr")
        spacers = self.raw_data.xpath(
            "//td[@class='spacer + bborder + lborder + rborder']/parent::tr")

        # setting up tree to generate explicit xpath expressions for
        # considered elements
        tree = etree.ElementTree(self.raw_data)

        for h, s in zip(headings, spacers):
            # retrieving player's jersey number
            no = int(h.xpath("td/text()")[0].split()[0])
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
