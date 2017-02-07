#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope


class Contract(Base):
    __tablename__ = 'contracts'
    __autoload__ = True


def __init__(self, player_id, contract_data):


