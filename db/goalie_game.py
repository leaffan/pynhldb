#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope


class GoalieGame(Base):
    __tablename__ = 'goalie_games'
    __autoload__ = True

    HUMAN_READABLE = 'goalie game'

    STANDARD_ATTRS = [
        "no", "shots_against", "goals_against", "saves", "en_goals",
        "toi_overall", "toi_pp", "toi_sh", "toi_ev", "win", "loss", "otl",
        "tie", "regulation_tie", "overtime_game", "shootout_game",
        "shutout", "gaa", "save_pctg", "starting",
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
                if attr == "starting":
                    setattr(self, attr, False)
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
            except Exception as e:
                plr_game = None
            return plr_game

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.game_id, self.player_id, self.team_id, self.no,
                self.shots_against, self.goals_against, self.saves,
                self.en_goals, self.toi_overall, self.toi_pp, self.toi_sh,
                self.toi_ev, self.win, self.loss, self.otl, self.tie,
                self.regulation_tie, self.overtime_game, self.shootout_game,
                self.shutout, self.starting,
                None if self.gaa is None else "{0:f}".format(
                    round(self.gaa, 6)),
                None if self.save_pctg is None else "{0:f}".format(
                    round(self.save_pctg, 6))
            ) == (
                other.game_id, other.player_id, other.team_id, other.no,
                other.shots_against, other.goals_against, other.saves,
                other.en_goals, other.toi_overall, other.toi_pp, other.toi_sh,
                other.toi_ev, other.win, other.loss, other.otl, other.tie,
                other.regulation_tie, other.overtime_game, other.shootout_game,
                other.shutout, other.starting,
                None if other.gaa is None else "{0:f}".format(
                    round(other.gaa, 6)),
                None if other.save_pctg is None else "{0:f}".format(
                    round(other.save_pctg, 6))
                ))

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return "%s(%d)" % (self.__class__.__name__, self.goalie_game_id)
