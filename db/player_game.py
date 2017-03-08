#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope
from .player import Player


class PlayerGame(Base):
    __tablename__ = 'player_games'
    __autoload__ = True

    STANDARD_ATTRS = [
        "position", "no", "goals", "assists", "primary_assists",
        "secondary_assists", "points", "plus_minus", "penalties", "pim",
        "toi_overall", "toi_pp", "toi_sh", "toi_ev", "avg_shift", "no_shifts",
        "shots_on_goal", "shots_blocked", "shots_missed", "hits",
        "giveaways", "takeaways", "blocks", "faceoffs_won", "faceoffs_lost",
        "on_ice_shots_on_goal", "on_ice_shots_blocked", "on_ice_shots_missed"
    ]

    def __init__(self, plr_game_id, game_id, team_id, plr_id, data_dict):
        self.player_game_id = plr_game_id
        self.player_game_id_2 = int("%d%02d%d" % (game_id, team_id, plr_id))
        self.game_id = game_id
        self.team_id = team_id
        self.player_id = plr_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])

    @classmethod
    def find(self, game_id, player_id):
        with session_scope() as session:
            try:
                plr_game = session.query(PlayerGame).filter(
                    and_(
                        PlayerGame.game_id == game_id,
                        PlayerGame.player_id == player_id
                    )).one()
            except:
                plr_game = None
            return plr_game

    def __str__(self):
        if not hasattr(self, 'player') or self.player is None:
            self.player = Player.find_by_id(self.player_id)
        return "%-40s %d G %d A %d Pts./%d PIM" % (
            self.player, self.goals, self.assists, self.points, self.pim)
