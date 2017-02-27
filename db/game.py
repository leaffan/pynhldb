#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope


class Game(Base):
    __tablename__ = 'games'
    __autoload__ = True

    def __init__(self, nhl_id, game_data_dict):
        self.game_id = nhl_id
        for attr in game_data_dict:
            setattr(self, attr, game_data_dict[attr])

    @classmethod
    def find(self, date, road_team, home_team):
        with session_scope() as session:
            try:
                g = session.query(Game).filter(
                    and_(
                        Game.date == date,
                        Game.road_team_id == road_team.team_id,
                        Game.home_team_id == home_team.team_id
                    )).one()
            except:
                g = None
        return g
