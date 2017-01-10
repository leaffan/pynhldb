#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

from .common import Base, session_scope
from .team import Team


class Division(Base):
    __tablename__ = 'divisions'
    __autoload__ = True

    def __init__(self, name, season, teams, conference=None):
        self.division_name = name
        self.season = season
        self.teams = list()
        for t in teams:
            self.teams.append(t.team_id)
        self.conference = conference

    @classmethod
    def get_divisions_and_teams(cls, season=None):

        if season is None:
            now = datetime.datetime.now()
            season = now.year - 1 if now.month <= 6 else now.year

        division_dict = dict()

        with session_scope() as session:
            divs = session.query(Division).filter(
                Division.season == season).all()
            for d in divs:
                teams = list()
                for team_id in d.teams:
                    team = Team.find_by_id(team_id)
                    teams.append(team)
                division_dict[d.division_name] = teams

        return division_dict

    def __str__(self):
        if self.conference:
            base_information_str = "%s Division (%s Conference) %s:" % (
                self.division_name, self.conference, self.season)
        else:
            base_information_str = "%s Division %s:" % (
                self.division_name, self.season)

        team_information_str = "\n\t+ ".join(
            sorted([Team.find_by_id(team_id).name for team_id in self.teams]))

        return "\n\t+ ".join((base_information_str, team_information_str))
