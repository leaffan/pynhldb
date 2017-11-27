#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope
from .player import Player


class PlayerGame(Base):
    __tablename__ = 'player_games'
    __autoload__ = True

    HUMAN_READABLE = 'player game'

    STANDARD_ATTRS = [
        "position", "no", "goals", "assists", "primary_assists",
        "secondary_assists", "points", "plus_minus", "penalties", "pim",
        "toi_overall", "toi_pp", "toi_sh", "toi_ev", "avg_shift", "no_shifts",
        "shots_on_goal", "shots_blocked", "shots_missed", "hits",
        "giveaways", "takeaways", "blocks", "faceoffs_won", "faceoffs_lost",
        "on_ice_shots_on_goal", "on_ice_shots_blocked", "on_ice_shots_missed",
        "captain", "alternate_captain", "starting"
    ]

    def __init__(self, game_id, team_id, plr_id, data_dict):
        self.player_game_id = int("%d%02d%d" % (game_id, team_id, plr_id))
        self.game_id = game_id
        self.team_id = team_id
        self.player_id = plr_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                if attr in ("captain", "alternate_captain", "starting"):
                    setattr(self, attr, False)
                else:
                    setattr(self, attr, None)

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

    def get_player(self):
        return Player.find_by_id(self.player_id)

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            # assuring boolean attributes don't get set to null
            if attr in ['starting', 'captain', 'alternate_captain']:
                if getattr(other, attr) is True:
                    setattr(self, attr, True)
                else:
                    setattr(self, attr, False)
            # updating regular attributes
            else:
                setattr(self, attr, getattr(other, attr))

    # TODO: include further attributes
    def __eq__(self, other):
        return (
            (
                self.no, self.position, self.goals, self.assists,
                self.primary_assists, self.secondary_assists, self.points,
                self.plus_minus, self.penalties, self.pim,
                self.toi_overall, self.toi_pp, self.toi_sh, self.toi_ev,
                self.avg_shift, self.no_shifts, self.shots_on_goal,
                self.shots_blocked, self.shots_missed, self.hits,
                self.giveaways, self.takeaways,
                self.blocks, self.faceoffs_won, self.faceoffs_lost,
                self.starting, self.captain, self.alternate_captain,
                # self.on_ice_shots_on_goal, self.on_ice_shots_missed,
                # self.on_ice_shots_blocked
                ) == (
                other.no, other.position, other.goals, other.assists,
                other.primary_assists, other.secondary_assists, other.points,
                other.plus_minus, other.penalties, other.pim,
                other.toi_overall, other.toi_pp, other.toi_sh, other.toi_ev,
                other.avg_shift, other.no_shifts, other.shots_on_goal,
                other.shots_blocked, other.shots_missed, other.hits,
                other.giveaways, other.takeaways,
                other.blocks, other.faceoffs_won, other.faceoffs_lost,
                other.starting, other.captain, other.alternate_captain,
                # other.on_ice_shots_on_goal, other.on_ice_shots_missed,
                # other.on_ice_shots_blocked
                ))

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        if not hasattr(self, 'player') or self.player is None:
            self.player = Player.find_by_id(self.player_id)
        return "%-40s %d G %d A %d Pts./%d PIM" % (
            self.player, self.goals, self.assists, self.points, self.pim)
