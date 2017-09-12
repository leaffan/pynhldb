#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from sqlalchemy import and_

from .common import Base, session_scope


class Contract(Base):
    __tablename__ = 'contracts'
    __autoload__ = True

    HUMAN_READABLE = 'contract'

    STANDARD_ATTRS = [
        'signing_team_id', 'signing_date', 'length', 'value', 'type',
        'expiry_status', 'source', 'start_season', 'end_season',
        'cap_hit_percentage', 'bought_out', 'notes'
        ]

    def __init__(self, player_id, contract_data_dict):
        self.contract_id = uuid.uuid4().urn
        self.player_id = player_id
        for attr in self.STANDARD_ATTRS:
            if attr in contract_data_dict:
                setattr(self, attr, contract_data_dict[attr])
            else:
                if attr in ['bought_out']:
                    setattr(self, attr, False)
                else:
                    setattr(self, attr, None)

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

    @classmethod
    def find_with_team(
            self, player_id, start_season, end_season, signing_team_id):
        with session_scope() as session:
            try:
                contract = session.query(Contract).filter(
                    and_(
                        Contract.player_id == player_id,
                        Contract.start_season == start_season,
                        Contract.end_season == end_season,
                        Contract.signing_team_id == signing_team_id
                    )
                ).one()
            except:
                contract = None
            return contract

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return ((
            self.player_id, self.signing_team_id, self.signing_date,
            self.length, self.value, self.type, self.expiry_status,
            self.source, self.start_season, self.end_season, self.notes,
            "%.2f" % round(self.cap_hit_percentage, 2), self.bought_out
            ) == (
            other.player_id, other.signing_team_id, other.signing_date,
            other.length, other.value, other.type, other.expiry_status,
            other.source, other.start_season, other.end_season, other.notes,
            "%.2f" % round(other.cap_hit_percentage, 2), other.bought_out))

    def __ne__(self, other):
        return not self == other
