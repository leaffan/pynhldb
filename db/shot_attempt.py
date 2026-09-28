#!/usr/bin/env python

import uuid

from db.common import Base
from db.specific_event import SpecificEvent


class ShotAttempt(Base, SpecificEvent):
    __tablename__ = 'shot_attempts'
    __autoload__ = True

    HUMAN_READABLE = 'shot attempt'

    # one row per shot-attempt event (not per on-ice player), with the
    # on-ice rosters of both teams stored as player id arrays
    STANDARD_ATTRS = [
        "game_id", "event_id", "shot_attempt_type", "num_situation",
        "plr_situation", "score_diff", "for_team_id", "against_team_id",
        "shooter_id", "for_player_ids", "against_player_ids"
    ]

    def __init__(self, game_id, event_id, data_dict):
        self.shot_attempt_id = uuid.uuid4().urn
        self.game_id = game_id
        self.event_id = event_id
        for attr in data_dict:
            setattr(self, attr, data_dict[attr])
