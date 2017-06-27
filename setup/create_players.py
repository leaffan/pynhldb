#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from concurrent.futures import ThreadPoolExecutor, as_completed

from db import commit_db_item
from db.player import Player
from db.team import Team
from utils.player_finder import PlayerFinder
from utils.player_data_retriever import PlayerDataRetriever

MAX_WORKERS = 8


def migrate_players(plr_src_file=None):

    if not plr_src_file:
        plr_src_file = os.path.join(
            os.path.dirname(__file__), 'nhl_players.json')

    migration_data = json.load(open(plr_src_file))

    for player_id in sorted(migration_data.keys())[:]:

        last_name = migration_data[player_id]['last_name']
        first_name = migration_data[player_id]['first_name']
        position = migration_data[player_id]['position']

        alternate_last_names = migration_data[player_id].get(
            'alternate_last_names', None)
        alternate_first_names = migration_data[player_id].get(
            'alternate_first_names', None)
        alternate_positions = migration_data[player_id].get(
            'alternate_positions', None)

        plr = Player(
            player_id, last_name, first_name, position,
            alternate_last_names=alternate_last_names,
            alternate_first_names=alternate_first_names,
            alternate_positions=alternate_positions
        )

        print("Working on %s" % plr)

        commit_db_item(plr)


def search_players(src_type):

    plr_f = PlayerFinder()
    plr_r = PlayerDataRetriever()

    current_teams = Team.find_teams_for_season()
    for team in sorted(current_teams)[:]:
        team_players = plr_f.find_players_for_team(team, src_type)

        # using concurrent threads to speed up the retrieval of single player
        # season statistics
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as threads:
            future_tasks = {
                threads.submit(
                    plr_r.retrieve_player_seasons,
                    plr.player_id): plr for plr in team_players}
            for future in as_completed(future_tasks):
                try:
                    # TODO: think of something to do with the result here
                    data = future.result()
                except Exception as e:
                    print
                    print("Conccurrent task generated an exception: %s" % e)
