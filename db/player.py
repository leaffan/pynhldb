#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope


class Player(Base):
    __tablename__ = 'players'
    __autoload__ = True

    ALTERNATE_VALUE_KEYWORDS = [
        'alternate_last_names',
        'alternate_first_names',
        'alternate_positions',
    ]

    def __init__(self, nhl_id, last_name, first_name, position, **kwargs):
        self.player_id = int(nhl_id)
        self.last_name = last_name
        self.first_name = first_name
        self.position = position

        for keyword in self.ALTERNATE_VALUE_KEYWORDS:
            if keyword in kwargs:
                self.set_keyword_argument(keyword, kwargs[keyword])

    def set_keyword_argument(self, keyword, value):
        if value is not None and type(value) is not list:
            value = [value]
        setattr(self, keyword, value)

    @property
    def name(self):
        return " ".join((self.first_name, self.last_name))

    @classmethod
    def find_by_id(self, nhl_id):
        with session_scope() as session:
            try:
                player = session.query(Player).filter(
                    Player.player_id == nhl_id
                ).one()
            except:
                player = None
            return player

    def __str__(self):
        return "[%d] %s" % (self.player_id, self.name)

    def __eq__(self, other):
        return self.player_id == other.player_id

    def __ne__(self, other):
        return not self == other

