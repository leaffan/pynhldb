#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope

from sqlalchemy import and_


class Contract(Base):
    __tablename__ = 'contracts'
    __autoload__ = True

    STANDARD_ATTRS = [
        'signing_team_id', 'signing_date', 'length', 'value', 'type',
        'expiry_status', 'source', 'start_season', 'end_season',
        'cap_hit_percentage', 'bought_out'
        ]

    def __init__(self, player_id, contract_data_dict):

        self.player_id = player_id
        for attr in self.STANDARD_ATTRS:
            if attr in contract_data_dict:
                setattr(self, attr, contract_data_dict[attr])

    @classmethod
    def find(self, player_id, start_season, end_season):
        with session_scope() as session:
            try:
                contract = session.query(Contract).filter(
                    and_(
                        Contract.player_id == player_id,
                        Contract.start_season == start_season,
                        Contract.end_season == end_season
                    )
                ).one()
            except:
                contract = None
            return contract
