#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from sqlalchemy import and_

from db.common import Base, session_scope
from db.specific_event import SpecificEvent


class ShotAttempt(Base, SpecificEvent):
    __tablename__ = 'shot_attempts'
    __autoload__ = True

    HUMAN_READABLE = 'shot attempt'

    STANDARD_ATTRS = [
        "game_id", "team_id", "event_id", "player_id", "shot_attempt_type",
        "plus_minus", "num_situation", "plr_situation", "actual", "score_diff"
    ]

    def __init__(self, game_id, team_id, event_id, player_id, data_dict):
        self.shot_attempt_id = uuid.uuid4().urn
        self.game_id = game_id
        self.team_id = team_id
        self.event_id = event_id
        self.player_id = player_id
        for attr in data_dict:
            setattr(self, attr, data_dict[attr])

    @classmethod
    def find_by_event_player_id(self, event_id, player_id):
        with session_scope() as session:
            try:
                shot_attempt = session.query(ShotAttempt).filter(
                    and_(
                        ShotAttempt.event_id == event_id,
                        ShotAttempt.player_id == player_id
                    )
                ).one()
            except Exception as e:
                shot_attempt = None
            return shot_attempt
