#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope


class ContractYear(Base):
    __tablename__ = 'contract_years'
    __autoload__ = True

    STANDARD_ATTRS = [
        'season', 'cap_hit', 'aav', 'sign_bonus', 'perf_bonus',
        'nhl_salary', 'minors_salary', 'clause', 'bought_out',
        ]

    def __init__(self, player_id, contract_id, contract_year_data_dict):
        self.player_id = player_id
        self.contract_id = contract_id
        for attr in self.STANDARD_ATTRS:
            if attr in contract_year_data_dict:
                setattr(self, attr, contract_year_data_dict[attr])

    @classmethod
    def find(self, player_id, contract_id, season):
        with session_scope() as session:
            try:
                contract_year = session.query(ContractYear).filter(
                    and_(
                        ContractYear.player_id == player_id,
                        ContractYear.contract_id == contract_id,
                        ContractYear.season == season,
                    )
                ).one()
            except:
                contract_year = None
            return contract_year

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return ((
            self.player_id, self.season, self.cap_hit, self.aav,
            self.nhl_salary, self.sign_bonus, self.perf_bonus,
            self.minors_salary, self.clause, self.note, self.bought_out
            ) == (
            other.player_id, other.season, other.cap_hit, other.aav,
            other.nhl_salary, other.sign_bonus, other.perf_bonus,
            other.minors_salary, other.clause, other.note, other.bought_out))

    def __ne__(self, other):
        return not self == other
