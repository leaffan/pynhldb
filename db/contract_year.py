#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base


class ContractYear(Base):
    __tablename__ = 'contract_years'
    __autoload__ = True

    STANDARD_ATTRS = [
        'season', 'cap_hit', 'aav', 'sign_bonus', 'perf_bonus',
        'nhl_salary', 'minors_salary', 'claus', 'bought_out',
        ]

    def __init__(self, player_id, contract_year_data_dict):
        self.player_id = player_id
        for attr in self.STANDARD_ATTRS:
            if attr in contract_year_data_dict:
                setattr(self, attr, contract_year_data_dict[attr])
