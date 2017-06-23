#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.player import Player
from db.event import Event
from db.team import Team


class Shot(Base, SpecificEvent):
    __tablename__ = 'shots'
    __autoload__ = True

    HUMAN_READABLE = 'shot'

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "goalie_team_id", "goalie_id",
        "shot_type", "distance", "scored", "penalty_shot"
    ]

    def __init__(self, event_id, data_dict):
        self.shot_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                if attr in ['scored', 'penalty_shot']:
                    setattr(self, attr, False)
                else:
                    setattr(self, attr, None)

    def __str__(self):
        player = Player.find_by_id(self.player_id)
        goalie = Player.find_by_id(self.goalie_id)
        plr_team = Team.find_by_id(self.team_id)
        goalie_team = Team.find_by_id(self.goalie_team_id)
        event = Event.find_by_id(self.event_id)
        if goalie is not None:
            return "Shot: %s (%s) %s, %d ft vs. %s (%s) - %s" % (
                player.name, plr_team.abbr, self.shot_type, self.distance,
                goalie.name, goalie_team.abbr, event)
        else:
            return "Shot: %s (%s) %s, %d ft - %s" % (
                player.name, plr_team.abbr,
                self.shot_type, self.distance,
                event)
