#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.event import Event
from db.player import Player
from db.team import Team


class Block(Base, SpecificEvent):
    __tablename__ = 'blocks'
    __autoload__ = True

    HUMAN_READABLE = 'block'

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
        blocked_team = Team.find_by_id(self.blocked_team_id)
        blocking_team = Team.find_by_id(self.team_id)
        event = Event.find_by_id(self.event_id)
        if blocking_plr is None:
            return_str = (
                f"Blocked Shot: Teammmate ({blocking_team.abbr}) on {blocked_plr.name} ({blocked_team.abbr}) " +
                f"{self.shot_type} - {event}"
            )
        else:
            return_str = (
                f"Blocked Shot: {blocking_plr.name} ({blocking_team.abbr}) on {blocked_plr.name} " +
                f"({blocked_team.abbr}) {self.shot_type} - {event}"
            )

        return return_str
