#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope


class Player(Base):
    __tablename__ = 'players'
    __autoload__ = True

    def __init__(self):
        pass
