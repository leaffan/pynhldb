#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from collections import defaultdict

from utils import str_to_timedelta
from db import create_or_update_db_item
from db.event import Event

logger = logging.getLogger(__name__)


class EventParser():

    def __init__(self, raw_data):
        self.raw_data = raw_data
        # class-wide variables to hold current score for both home and road
        # team, increase accordingly if a goal was score
        self.home_score = 0
        self.road_score = 0
        self.score_diff = 0
        # self.curr_period = 0

    def create_events(self, game, rosters):
        self.game = game
        self.rosters = rosters

        self.load_data()

        for event_data_item in self.event_data:
            event = self.get_event(event_data_item)

        if self.game.type == 2 and event.period == 5:
            # shootout attempts are either goals, saved shots or misses all
            # occurring in the fifth period of a regular season game
            shootout_attempt = self.get_shootout_attempt(event)
        else:
            # specifying regular play-by-play event
            self.specify_event(event)

    def specify_event(self, event):
        """
        Specifies an event in more detail according to its type.
        """
        if event.type in ['SHOT', 'GOAL']:
            shot = self.get_shot_event(event)

        if event.type == 'GOAL':
            shot = Shot.find_by_event_id(event.event_id)
            goal = self.get_goal_event(event, shot)

        if event.type == 'MISS':
            miss = self.get_miss_event(event)

        if event.type == 'BLOCK':
            block = self.get_block_event(event)

        if event.type == 'FAC':
            faceoff = self.get_faceoff_event(event)

        if event.type == 'HIT':
            hit = self.get_hit_event(event)

        if event.type == 'GIVE':
            giveaway = self.get_giveaway_event(event)

        if event.type == 'TAKE':
            takeaway = self.get_takeaway_event(event)

        if event.type == 'PENL':
            penalty = self.get_penalty_event(event)

    def get_event(self, event_data_item):
        """
        Gets basic event information first and triggers type-specific parsing
        afterwards.
        """
        # retrieving data item contents as list
        tokens = event_data_item.xpath("td/text()")
        # setting up event data dictionary
        event_data_dict = dict()
        # TODO: decide whether to put game id directly in constructor
        event_data_dict['game_id'] = self.game.game_id
        event_data_dict['home_score'] = self.home_score
        event_data_dict['road_score'] = self.road_score

        # retrieving basic event attributes
        event_data_dict['in_game_event_cnt'] = int(tokens[0])
        event_data_dict['period'] = int(tokens[1])
        event_data_dict['time'] = str_to_timedelta(tokens[3])
        event_data_dict['type'] = tokens[5]
        event_data_dict['raw_data'] = tokens[6]

        # stoppages in play are registered as property of the according event
        if event_data_dict['type'] == 'STOP':
            event_data_dict['stop_type'] = event_data_dict['raw_data'].lower()

        # retrieving players on goalies on ice for current event
        players_on_ice, goalies_on_ice = self.retrieve_players_on_ice(
            event_data_item)
        for key in ['home', 'road']:
            event_data_dict["%s_on_ice" % key] = players_on_ice[key]
            if key in goalies_on_ice:
                event_data_dict["%s_goalie" % key] = goalies_on_ice[key]

        # creating event id
        event_id = "{0:d}{1:04d}".format(
            self.game.game_id, event_data_dict['in_game_event_cnt'])

        # setting up new event item
        event = Event(event_id, event_data_dict)
        # trying to find existing event item in database
        db_event = Event.find(
            self.game.game_id, event_data_dict['in_game_event_cnt'])
        # updating existing or creating new event item
        create_or_update_db_item(db_event, event)

        return Event.find(
            self.game.game_id, event_data_dict['in_game_event_cnt'])

    def retrieve_players_on_ice(self, event_data_item):
        """
        Gets all players and goalies on ice for current event and each team.
        """
        poi_data = dict()
        players_on_ice = defaultdict(list)
        goalies_on_ice = dict()

        try:
            poi_data['road'], poi_data['home'] = event_data_item.xpath(
                "td/table")
        except:
            return players_on_ice, goalies_on_ice

        for key in ['road', 'home']:
            # retrieving jersey numbers of players on ice for current event
            nos_on_ice = [int(n) for n in poi_data[key].xpath(
                "tr/td/table/tr/td/font/text()")]
            # retrieving positions of players on ice for current event
            pos_on_ice = [s for s in poi_data[key].xpath(
                "tr/td/table/tr/td/text()") if s not in ['\r\n', '\n']]
            # checking whether as many numbers as positions have been retrieved
            if len(pos_on_ice) != len(nos_on_ice):
                logger.warn(
                    "Number of retrieved jersey numbers does not match" +
                    "number of retrieved positions: game id %d, period %d" % (
                        self.game.game_id, self.curr_period))
                continue
            for no, pos in zip(nos_on_ice, pos_on_ice):
                # retrieving actual player from rosters of current game
                player = self.rosters[key][no]
                # and appending to list of players on ice
                players_on_ice[key].append(player.player_id)
                if pos == 'G':
                    goalies_on_ice[key] = player.player_id

        return players_on_ice, goalies_on_ice

    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        self.event_data = list()
        # finding all table rows on play-by-play page
        for tr in self.raw_data.xpath("body/table/tr"):
            # adding table row to play-by-play info if the first entry is a
            # digit, i.e. an in-game event id
            try:
                int(tr.xpath("td[1]/text()")[0])
                self.event_data.append(tr)
                # checking whether exactly eight table cells are located in row
                if len(tr.xpath("td")) != 8:
                    logger.warn(
                        "Unexpected number of table cells in play-by-play" +
                        "table row: %d" % len(tr.xpath("td")))
            except:
                logger.debug(
                    "Skipping row in play-by-play table")
                continue
