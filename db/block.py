#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base, session_scope


class Block(Base):
    __tablename__ = 'blocks'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "blocked_team_id", "blocked_player_id",
        "shot_type"
    ]

    def __init__(self, event_id, data_dict):
        self.block_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    @classmethod
    def find_by_event_id(self, event_id):
        with session_scope() as session:
            try:
                block = session.query(Block).filter(
                    Block.event_id == event_id
                ).one()
            except:
                block = None
            return block

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.event_id, self.team_id, self.player_id, self.zone,
                self.blocked_team_id, self.blocked_player_id, self.shot_type,
                ) == (
                other.event_id, other.team_id, other.player_id, other.zone,
                other.blocked_team_id, other.blocked_player_id,
                other.shot_type,
                ))

    def __ne__(self, other):
        return not self == other
