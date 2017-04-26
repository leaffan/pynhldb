#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.event import Event
from db.player import Player


class Block(Base, SpecificEvent):
    __tablename__ = 'blocks'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "shot_type",
        "blocked_team_id", "blocked_player_id"
    ]

    def __init__(self, event_id, data_dict):
        self.block_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    def __str__(self):
        blocked_plr = Player.find_by_id(self.blocked_player_id)
        blocking_plr = Player.find_by_id(self.player_id)
        event = Event.find_by_id(self.event_id)
        return "Blocked Shot: %s from %s (%s) (%d/%s)" % (
            blocking_plr.name, blocked_plr.name,
            self.shot_type, event.period, event.time)
