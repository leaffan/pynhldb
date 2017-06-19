#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope

from sqlalchemy import and_, or_
from sqlalchemy.sql.expression import func


class Team(Base):
    __tablename__ = 'teams'
    __autoload__ = True

    def __init__(self, team_data):
        self.team_id = team_data.get('id')
        self.franchise_id = team_data.get('franchise')['franchiseId']
        self.name = team_data.get('name')
        self.short_name = team_data.get('shortName')
        self.team_name = team_data.get('teamName')
        self.abbr = team_data.get('abbreviation')
        self.first_year_of_play = team_data.get('firstYearOfPlay')

    @classmethod
    def find(cls, abbr):
        with session_scope() as session:
            t = session.query(Team).filter(
                or_(
                    func.lower(Team.abbr) == abbr.lower(),
                    func.lower(Team.orig_abbr) == abbr.lower())).first()
            return t

    @classmethod
    def find_by_name(cls, name):

        if name.lower() in [
                "canadiens montreal",
                "montreal canadiens",
                "canadien de montreal"]:
                    name = "Montréal Canadiens"

        with session_scope() as session:
            try:
                t = session.query(Team).filter(
                    func.lower(Team.name) == name.lower()
                ).one()
            except:
                t = None
            return t

    @classmethod
    def find_by_id(cls, id):
        with session_scope() as session:
            try:
                t = session.query(Team).filter(
                    Team.team_id == id
                ).one()
            except:
                t = None
            return t

    @classmethod
    def find_by_abbr(cls, abbr):
        with session_scope() as session:
            try:
                t = session.query(Team).filter(
                    or_(
                        func.lower(Team.abbr) == abbr.lower(),
                        func.lower(Team.orig_abbr) == abbr.lower()
                    )
                ).one()
            except:
                t = None
            return t

    @classmethod
    def find_teams_for_season(cls, season=None):
        with session_scope() as session:
            if season is None:
                teams = session.query(Team).filter(
                    Team.last_year_of_play.is_(None)
                ).all()
            else:
                teams = session.query(Team).filter(
                    and_(
                        Team.first_year_of_play <= season,
                        or_(
                            Team.last_year_of_play > season,
                            Team.last_year_of_play.is_(None)
                        )
                    )
                ).all()
            return teams

    def __str__(self):
        return self.name

    def __hash__(self):
        return self.team_id

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        return self.name > other.name

    def __lt__(self, other):
        return self.name < other.name
