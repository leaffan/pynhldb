#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from db import commit_db_item
from db.player import Player


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
