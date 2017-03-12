#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope


class GoalieGame(Base):
    __tablename__ = 'goalie_games'
    __autoload__ = True

    STANDARD_ATTRS = [
        "position", "no", "goals", "assists", "primary_assists",
        "secondary_assists", "points", "plus_minus", "penalties", "pim",
        "toi_overall", "toi_pp", "toi_sh", "toi_ev", "avg_shift", "no_shifts",
        "shots_on_goal", "shots_blocked", "shots_missed", "hits",
        "giveaways", "takeaways", "blocks", "faceoffs_won", "faceoffs_lost",
        "on_ice_shots_on_goal", "on_ice_shots_blocked", "on_ice_shots_missed"
    ]

    def __init__(self, game_id, team_id, plr_id, data_dict):
        self.goalie_game_id = int("%d%02d%d" % (game_id, team_id, plr_id))
        self.game_id = game_id
        self.team_id = team_id
        self.player_id = plr_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    @classmethod
    def find(self, game_id, player_id):
        with session_scope() as session:
            try:
                plr_game = session.query(GoalieGame).filter(
                    and_(
                        GoalieGame.game_id == game_id,
                        GoalieGame.player_id == player_id
                    )).one()
            except:
                plr_game = None
            return plr_game

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

