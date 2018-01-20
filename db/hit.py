#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.event import Event
from db.player import Player
from db.team import Team


class Hit(Base, SpecificEvent):
    __tablename__ = 'hits'
    __autoload__ = True

    HUMAN_READABLE = 'miss'

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone",
        "hit_taken_team_id", "hit_taken_player_id",
    ]

    def __init__(self, event_id, data_dict):
        self.hit_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    def __str__(self):
        hit_plr = Player.find_by_id(self.player_id)
        taken_plr = Player.find_by_id(self.hit_taken_player_id)
        hit_team = Team.find_by_id(self.team_id)
        taken_team = Team.find_by_id(self.hit_taken_team_id)
        event = Event.find_by_id(self.event_id)
        
        if taken_plr is None:
            taken = "unknown"
        else:
            taken = taken_plr.name

        if hit_plr is None:
            hit = "unknown"
        else:
            hit = hit_plr.name
        
        return "Hit: %s (%s) on %s (%s) - %s" % (
            hit, hit_team.abbr, taken, taken_team.abbr, event)
