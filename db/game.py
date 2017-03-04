#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope
from .team import Team


class Game(Base):
    __tablename__ = 'games'
    __autoload__ = True

    STANDARD_ATTRS = [
        "attendance", "data_last_modified", "date", "end", "game_id",
        "home_game_count", "home_overall_game_count", "home_score",
        "home_team_id", "overtime_game", "road_game_count",
        "road_overall_game_count", "road_score", "road_team_id",
        "season", "shootout_game", "start", "type", "venue"
    ]

    def __init__(self, game_data_dict):
        for attr in self.STANDARD_ATTRS:
            if attr in game_data_dict:
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

    def __str__(self):
        road_team = Team.find_by_id(self.road_team_id)
        home_team = Team.find_by_id(self.home_team_id)
        return "%-25s (%d) @ %-25s (%d) [%s/%s]" % (
            road_team.name, self.road_score,
            home_team.name, self.home_score,
            self.date, self.game_id)
