#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from db.common import Base, session_scope
from db.team import Team


class TeamGame(Base):
    __tablename__ = 'team_games'
    __autoload__ = True

    STANDARD_ATTRS = [
        "score", "goals_for_1st", "goals_against_1st", "goals_for_2nd",
        "goals_against_2nd", "goals_for_3rd", "goals_against_3rd", "goals_for",
        "goals_against", "win", "regulation_win", "overtime_win",
        "shootout_win", "loss", "regulation_loss", "overtime_loss",
        "shootout_loss", "tie", "pp_overall", "pp_time_overall", "pp_5v4",
        "pp_time_5v4", "pp_4v3", "pp_time_4v3", "pp_5v3", "pp_time_5v3",
        "shots_for", "shots_against", "shots_for_1st", "shots_against_1st",
        "shots_for_2nd", "shots_against_2nd", "shots_for_3rd",
        "shots_against_3rd", "shots_for_ot", "shots_against_ot", "so_attempts",
        "so_goals", "penalties", "pim", "points", "home_road_type"
    ]

    def __init__(self, game_id, team_id, data_dict):
        self.team_game_id = int("%d%02d" % (game_id, team_id))
        self.game_id = game_id
        self.team_id = team_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    @classmethod
    def find(self, game_id, team_id):
        with session_scope() as session:
            try:
                team_game = session.query(TeamGame).filter(
                    and_(
                        TeamGame.game_id == game_id,
                        TeamGame.team_id == team_id
                    )).one()
            except:
                team_game = None
            return team_game

    def get_team(self):
        return Team.find_by_id(self.team_id)

    def update(self, other):
        print("self", self.home_road_type)
        print("other", other.home_road_type)
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        # comparing each standard attribute value (and game and team id) of
        # this object with other one's
        print("s", self.home_road_type)
        print("o", other.home_road_type)
        print("ss", [self.team_id].extend([1, 2, 3]))#.extend([getattr(self, attr) for attr in self.STANDARD_ATTRS]))
        print("oo", [other.game_id, other.team_id].extend(
            [getattr(other, attr) for attr in other.STANDARD_ATTRS]))
        return [self.game_id, self.team_id].extend(
            [getattr(self, attr) for attr in self.STANDARD_ATTRS]
        ) == [other.game_id, other.team_id].extend(
            [getattr(other, attr) for attr in other.STANDARD_ATTRS]
        )

    def __ne__(self, other):
        return not self == other
