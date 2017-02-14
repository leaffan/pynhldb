#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope


class Buyout(Base):
    __tablename__ = 'buyouts'
    __autoload__ = True

    STANDARD_ATTRS = [
        'buyout_team_id', 'buyout_date', 'length', 'value',
        'start_season', 'end_season'
        ]

    def __init__(self, player_id, contract_id, buyout_data_dict):
        self.player_id = player_id
        self.contract_id = contract_id
        for attr in self.STANDARD_ATTRS:
            if attr in buyout_data_dict:
                setattr(self, attr, buyout_data_dict[attr])

    @classmethod
    def find(self, contract_id):
        with session_scope() as session:
            try:
                buyout = session.query(Buyout).filter(
                    Buyout.contract_id == contract_id
                ).one()
            except:
                buyout = None
            return buyout

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return ((
            self.contract_id, self.player_id, self.buyout_team_id,
            self.buyout_date, self.length, self.value,
            self.start_season, self.end_season
            ) == (
            other.contract_id, other.player_id, other.buyout_team_id,
            other.buyout_date, other.length, other.value,
            other.start_season, other.end_season))

    def __ne__(self, other):
        return not self == other
