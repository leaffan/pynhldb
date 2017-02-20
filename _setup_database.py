#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from setup.create_teams import migrate_teams
from setup.create_divisions import create_divisions
from setup.create_players import migrate_players
from setup.create_player_data import create_player_seasons
from setup.create_player_data import create_player_data
from setup.create_player_data import create_player_contracts
from setup.create_player_data import create_player_drafts
from setup.create_player_data import create_capfriendly_ids
from setup.create_player_data import create_capfriendly_ids_by_team

from utils import prepare_logging
prepare_logging(log_types=['file', 'screen'])


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Setup script for NHL database creation.')
    parser.add_argument(
        'steps', metavar='setup_steps', help='Setup steps to execute.',
        choices=['a', 'c', 't', 'd', 'p', 'ps', 'pd', 'cf', 'cft', 'dft'])

    args = parser.parse_args()
    setup_steps = args.steps

    # migrating teams from json file to database
    if setup_steps in ['t', 'a']:
        migrate_teams()
    # creating divisions from division configuration file
    if setup_steps in ['d', 'a']:
        create_divisions()
    # migrating players from json file to database
    if setup_steps in ['p', 'a']:
        migrate_players()
    # retrieving player season statistics for all players in database
    if setup_steps in ['ps', 'a']:
        create_player_seasons()
    # retrieving individual player data for all players in database
    if setup_steps in ['pd', 'a']:
        create_player_data()
    # retrieving contract data for all players in database
    if setup_steps in ['c']:
        create_player_contracts()
    # retrieving draft data for all players in database
    if setup_steps in ['dft']:
        create_player_drafts()
    # retrieving capfriendly ids for all players in database
    if setup_steps in ['cf']:
        create_capfriendly_ids()
    # retrieving capfriendly ids for players of all teams in database
    if setup_steps in ['cft']:
        create_capfriendly_ids_by_team()
