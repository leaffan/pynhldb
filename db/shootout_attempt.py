#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base
from db.specific_event import SpecificEvent
from db.player import Player
from db.team import Team


class ShootoutAttempt(Base, SpecificEvent):
    __tablename__ = 'shootout_attempts'
    __autoload__ = True

    HUMAN_READABLE = 'shootout attempt'

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "goalie_team_id", "goalie_id",
        "attempt_type", "shot_type", "miss_type", "distance", "on_goal",
        "scored"
    ]

    def __init__(self, event_id, data_dict):
        self.shootout_attempt_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                if attr in ['scored', 'on_goal']:
                    setattr(self, attr, False)
                else:
                    setattr(self, attr, None)

    def __str__(self):
        player = Player.find_by_id(self.player_id)
        goalie = Player.find_by_id(self.goalie_id)
        plr_team = Team.find_by_id(self.team_id)
        goalie_team = Team.find_by_id(self.goalie_team_id)
        if self.attempt_type == 'GOAL':
            return "Shootout Goal: %s (%s) %s, %d ft. vs. %s (%s)" % (
                player.name, plr_team.abbr, self.shot_type, self.distance,
                goalie.name, goalie_team.abbr)
        elif self.attempt_type == 'MISS':
            return "Shootout Miss: %s (%s) %s, %d ft., %s vs. %s (%s)" % (
                player.name, plr_team.abbr, self.shot_type, self.distance,
                self.miss_type, goalie.name, goalie_team.abbr)
        elif self.attempt_type == 'SHOT':
            return "Shootout Shot: %s (%s) %s, %d ft. vs. %s (%s)" % (
                player.name, plr_team.abbr, self.shot_type, self.distance,
                goalie.name, goalie_team.abbr)
        elif self.attempt_type == 'FAIL':
            return "Shootout Fail: %s (%s)" % (
                player.name, plr_team.abbr)
