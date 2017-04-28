#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.event import Event
from db.player import Player


class Faceoff(Base, SpecificEvent):
    __tablename__ = 'faceoffs'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "faceoff_lost_team_id",
        "faceoff_lost_player_id", "faceoff_lost_zone"
    ]

    def __init__(self, event_id, data_dict):
        self.faceoff_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    def __str__(self):
        won_plr = Player.find_by_id(self.player_id)
        lost_plr = Player.find_by_id(self.faceoff_lost_player_id)
        event = Event.find_by_id(self.event_id)
        return "Faceoff: %s won vs. %s (%s) (%d/%s)" % (
            won_plr.name, lost_plr.name, self.zone, event.period, event.time)