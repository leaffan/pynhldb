#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.player import Player
from db.team import Team
from db.event import Event


class Penalty(Base, SpecificEvent):
    __tablename__ = 'penalties'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "drawn_team_id",
        "drawn_player_id", "served_player_id", "infraction", "pim"
    ]

    def __init__(self, event_id, penalty_data_dict):
        self.penalty_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in penalty_data_dict:
                setattr(self, attr, penalty_data_dict[attr])
            else:
                setattr(self, attr, None)

    def __str__(self):
        player = Player.find_by_id(self.player_id)
        team = Team.find_by_id(self.team_id)
        event = Event.find_by_id(self.event_id)
        if player is not None:
            return "Penalty: %s - %d minutes for %s (%d/%s)" % (
                player.name, self.pim, self.infraction,
                event.period, event.time)
        else:
            return "Penalty: %s bench - %d minutes for %s (%d/%s)" % (
                team, self.pim, self.infraction, event.period, event.time)
