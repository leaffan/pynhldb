#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

import requests

from db.common import session_scope
from db.team import Team


def migrate_teams(team_src_file=None, simulation=False):

    if not team_src_file:
        team_src_file = os.path.join(
            os.path.dirname(__file__), 'nhl_teams.json')

    migration_data = json.load(open(team_src_file))

    url_template = "https://statsapi.web.nhl.com/api/v1/teams/"

    with session_scope() as session:

        unused_slot_count = 0
        i = 0

        while unused_slot_count < 20:

            i += 1

            url = "".join((url_template, str(i)))
            response = requests.get(url)
            raw_data = response.json()

            if 'teams' not in raw_data:
                print("\t-> No team information found at url: %s" % url)
                unused_slot_count += 1
                continue

            for team_data in raw_data['teams']:
                print("+ Working on raw data for %s" % team_data['name'])

                if 'franchiseId' not in team_data:
                    print("-> %s is no NHL team" % team_data['name'])
                    continue

                t = Team(team_data)

                new_team_id = str(t.team_id)

                if new_team_id not in migration_data:
                    print("\t-> No team migration data found for %s" % t)
                    continue

                team_migration_data = migration_data[new_team_id]

                # integrating previously existing data
                for item in team_migration_data.keys():
                    if team_migration_data[item]:
                        setattr(t, item, team_migration_data[item])

                if not simulation:
                    session.add(t)
                    session.commit()

