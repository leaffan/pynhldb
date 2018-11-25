#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import traceback

from db.common import session_scope
from db.team import Team
from db.division import Division


def create_divisions(div_src_file=None):

    if not div_src_file:
        div_src_file = os.path.join(
            os.path.dirname(__file__), 'nhl_divisions_config.txt')

    lines = [l.strip() for l in open(div_src_file).readlines()]

    with session_scope() as session:

        session.query(Division).delete(synchronize_session=False)

        try:
            for line in lines:
                if line.startswith("#"):
                    continue
                division_name, season, teams, conference = line.split(";")
                season = int(season)
                team_abbrs = teams[1:-1].split(',')
                teams = list()
                for t in team_abbrs:
                    team = Team.find(t)
                    teams.append(team)
                else:
                    if conference:
                        division = Division(
                            division_name, season, teams, conference)
                    else:
                        division = Division(
                            division_name, season, teams)
                    session.add(division)

                    print(division)

            session.commit()

        except Exception as e:
            session.rollback()
            traceback.print_exc()
