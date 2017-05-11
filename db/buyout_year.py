#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope

from sqlalchemy import and_


class BuyoutYear(Base):
    __tablename__ = 'buyout_years'
    __autoload__ = True
    __human_readable__ = 'buyout year'

    STANDARD_ATTRS = ['season', 'cap_hit', 'cost']

    def __init__(self, player_id, buyout_id, buyout_year_data_dict):
        self.player_id = player_id
        self.buyout_id = buyout_id
        for attr in self.STANDARD_ATTRS:
            if attr in buyout_year_data_dict:
                setattr(self, attr, buyout_year_data_dict[attr])

    @classmethod
    def find(self, buyout_id, season):
        with session_scope() as session:
            try:
                buyout_year = session.query(BuyoutYear).filter(
                    and_(
                        BuyoutYear.buyout_id == buyout_id,
                        BuyoutYear.season == season
                    )
                ).one()
            except:
                buyout_year = None
            return buyout_year

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return ((
            self.buyout_id, self.season, self.cost, self.cap_hit
            ) == (
            other.buyout_id, other.season, other.cost, other.cap_hit))

    def __ne__(self, other):
        return not self == other
