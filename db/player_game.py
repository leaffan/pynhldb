#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base
from .player import Player


class PlayerGame(Base):
    __tablename__ = 'player_games'
    __autoload__ = True

    STANDARD_ATTRS = [
        "position", "no", "goals", "assists", "primary_assists",
        "secondary_assists", "points", "plus_minus", "penalties", "pim",
        "toi_overall", "toi_pp", "toi_sh", "toi_ev", "avg_shift", "no_shifts"
        "shots_on_goal", "shots_blocked", "shots_missed", "hits",
        "giveaways", "takeaways", "blocks", "faceoffs_won", "faceoffs_lost",
        "on_ice_shots_on_goal", "on_ice_shots_blocked", "on_ice_shots_missed"
    ]

    def __init__(self, plr_game_id, game_id, team_id, plr_id, data_dict):
        self.player_game_id = plr_game_id
        self.game_id = game_id
        self.team_id = team_id
        self.player_id = plr_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])

    def __str__(self):
        if not hasattr(self, 'player') or self.player is None:
            self.player = Player.find_by_id(self.player_id)
        return "%-40s %d G %d A %d Pts./%d PIM" % (
            self.player, self.goals, self.assists, self.points, self.pim)
