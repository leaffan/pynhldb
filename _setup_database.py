#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from setup.create_teams import migrate_teams
from setup.create_divisions import create_divisions
from setup.create_players import migrate_players
from setup.create_player_seasons import create_player_seasons
from setup.create_player_seasons import create_player_data
from setup.create_player_seasons import create_player_contracts

from utils import prepare_logging
prepare_logging(log_types=['file', 'screen'])


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Setup script for NHL database creation.')
    parser.add_argument(
        'steps', metavar='setup_steps', help='Setup steps to execute.',
        choices=['a', 'c', 't', 'd', 'p', 'ps', 'pd'])

    args = parser.parse_args()
    setup_steps = args.steps

    # migrating teams from json file to database
    if setup_steps in ['t', 'a']:
        migrate_teams(simulation=True)
    # creating divisions from division configuration file
    if setup_steps in ['d', 'a']:
        create_divisions(simulation=True)
    # migrating players from json file to database
    if setup_steps in ['p', 'a']:
        migrate_players(simulation=True)
    # retrieving player season statistics for all players in database
    if setup_steps in ['ps', 'a']:
        create_player_seasons(simulation=False)
    # retrieving individual player data for all players in database
    if setup_steps in ['pd', 'a']:
        create_player_data(simulation=False)

    if setup_steps in ['c']:
        create_player_contracts(simulation=False)
