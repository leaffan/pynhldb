#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base


class Miss(Base):
    __tablename__ = 'misses'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "goalie_team_id", "goalie_id",
        "shot_type", "distance", "scored", "penalty_shot"
    ]

    def __init__(self, event_id, data_dict):
        self.miss_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                if attr in ['scored', 'penalty_shot']:
                    setattr(self, attr, False)
                else:
                    setattr(self, attr, None)
