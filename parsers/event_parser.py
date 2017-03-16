#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventParser():

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.score = defaultdict(int)
        # self.score['road'] = 0
        # self.score['home'] = 0
        self.score_diff = 0
        self.curr_period = 0

    def create_events(self, game, rosters):
        self.game = game
        self.rosters = rosters

        self.load_data

        for event_data_item in self.event_data:
            self.get_event(event_data_item)

    def get_event(self, event_data_item):
        # retrieving data item contents as list
        tokens = event_data_item.xpath("td/text()")
        print(tokens)

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
                    # TODO: proper logging
                    print len(tr.xpath("td"))
            except:
                pass
