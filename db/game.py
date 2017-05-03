#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope
from .team import Team


class Game(Base):
    __tablename__ = 'games'
    __autoload__ = True

    STANDARD_ATTRS = [
        "attendance", "data_last_modified", "date", "end",
        "home_game_count", "home_overall_game_count", "home_score",
        "home_team_id", "overtime_game", "road_game_count",
        "road_overall_game_count", "road_score", "road_team_id",
        "season", "shootout_game", "start", "type", "venue"
    ]

    def __init__(self, game_id, game_data_dict):
        self.game_id = game_id
        for attr in self.STANDARD_ATTRS:
            if attr in game_data_dict:
                setattr(self, attr, game_data_dict[attr])

    @classmethod
    def find_by_id(self, game_id):
        with session_scope() as session:
            try:
                g = session.query(Game).filter(
                    Game.game_id == game_id
                ).one()
            except:
                g = None
        return g

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

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.season, self.type, self.start, self.end,
                self.date.strftime("%B %d, %Y"), self.attendance, self.venue,
                self.road_team_id, self.home_team_id, self.road_score,
                self.home_score, self.road_overall_game_count,
                self.home_overall_game_count, self.road_game_count,
                self.home_game_count) == (
                other.season, other.type, other.start,
                other.end, other.date.strftime("%B %d, %Y"),
                other.attendance, other.venue, other.road_team_id,
                other.home_team_id, other.road_score, other.home_score,
                other.road_overall_game_count, other.home_overall_game_count,
                other.road_game_count, other.home_game_count
            ))

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        return self.game_id > other.game_id

    def __lt__(self, other):
        return self.game_id < other.game_id

    def __str__(self):
        road_team = Team.find_by_id(self.road_team_id)
        home_team = Team.find_by_id(self.home_team_id)
        return "%-25s (%d) @ %-25s (%d) [%s/%d]" % (
            road_team.name, self.road_score,
            home_team.name, self.home_score,
            self.date, self.game_id)
