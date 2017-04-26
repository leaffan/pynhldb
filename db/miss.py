#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.player import Player
from db.event import Event


class Miss(Base, SpecificEvent):
    __tablename__ = 'misses'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "goalie_team_id", "goalie_id",
        "shot_type", "miss_type", "distance", "penalty_shot"
    ]

    def __init__(self, event_id, data_dict):
        self.miss_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                if attr in ['penalty_shot']:
                    setattr(self, attr, False)
                else:
                    setattr(self, attr, None)

    def __str__(self):
        player = Player.find_by_id(self.player_id)
        goalie = Player.find_by_id(self.goalie_id)
        event = Event.find_by_id(self.event_id)
        if goalie is not None:
            return "Missed Shot: %s (%s, %d ft) vs. %s (%d/%s)" % (
                player.name, self.miss_type, self.distance,
                goalie.name, event.period, event.time)
        else:
            return "Missed Shot: %s (%s, %d ft) (%d/%s)" % (
                player.name, self.miss_type, self.distance,
                event.period, event.time)
