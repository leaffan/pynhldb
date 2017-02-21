#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope


class PlayerDraft(Base):
    __tablename__ = 'player_drafts'
    __autoload__ = True

    def __init__(self, player_id, team_id, year, round, overall, dft_type='e'):
            self.player_id = player_id
            self.team_id = team_id
            self.year = year
            self.round = round
            self.overall = overall
            self.draft_type = dft_type

    @classmethod
    def find(cls, player_id, team_id, year):
        with session_scope() as session:
            try:
                plr_draft = session.query(PlayerDraft).filter(
                    and_(
                        PlayerDraft.player_id == player_id,
                        PlayerDraft.team_id == team_id,
                        PlayerDraft.year == year
                    )
                ).one()
            except:
                plr_draft = None
            return plr_draft

    @classmethod
    def find_by_player_id(cls, player_id):
        with session_scope() as session:
            try:
                plr_draft = session.query(PlayerDraft).filter(
                    PlayerDraft.player_id == player_id
                ).all()
            except:
                plr_draft = None
            return plr_draft

    def update(self, other):
        for attr in ['team_id', 'year', 'round', 'overall', 'draft_type']:
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            self.team_id, self.year, self.round,
            self.overall, self.draft_type
            ) == (
            other.team_id, other.year, other.round,
            other.overall, other.draft_type)

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        if self.year == other.year:
            if self.overall >= other.overall:
                return True
            else:
                return False
        else:
            if self.year > other.year:
                return True
            else:
                return False

    def __lt__(self, other):
        return not self.__gt__(other)
