#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope

from sqlalchemy import and_


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

