#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.event import Event
from db.player import Player
from db.team import Team


class Takeaway(Base, SpecificEvent):
    __tablename__ = 'takeaways'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "taken_from_team_id"
    ]

    def __init__(self, event_id, data_dict):
        self.takeaway_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    def __str__(self):
        plr = Player.find_by_id(self.player_id)
        event = Event.find_by_id(self.event_id)
        team = Team.find_by_id(self.team_id)
        return "Takeaway: %s (%s) - %s" % (
            plr.name, team.abbr, event)
