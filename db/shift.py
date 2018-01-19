#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope


class Shift(Base):
    __tablename__ = 'shifts'
    __autoload__ = True

    HUMAN_READABLE = 'shift'

    STANDARD_ATTRS = [
        "in_game_shift_cnt", "period", "start", "end", "duration"
    ]

    def __init__(self, game_id, team_id, player_id, data_dict):
        self.game_id = game_id
        self.team_id = team_id
        self.player_id = player_id
        # shift id is a combination of game id, team id, jersey number
        # and shift count
        self.shift_id = "%d%03d%02d%03d" % (
            game_id, team_id, data_dict['no'], data_dict['in_game_shift_cnt'])
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    @classmethod
    def find(self, game_id, player_id, in_game_cnt):
        with session_scope() as session:
            try:
                shift = session.query(Shift).filter(
                    and_(
                        Shift.game_id == game_id,
                        Shift.player_id == player_id,
                        Shift.in_game_shift_cnt == in_game_cnt
                    )).one()
            except Exception as e:
                shift = None
            return shift

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.game_id, self.team_id, self.player_id,
                self.in_game_shift_cnt, self.period,
                self.start, self.end, self.duration
                ) == (
                other.game_id, other.team_id, other.player_id,
                other.in_game_shift_cnt, other.period,
                other.start, other.end, other.duration
            ))

    def __ne__(self, other):
        return not self == other
