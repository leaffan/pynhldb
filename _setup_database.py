#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from setup.create_teams import migrate_teams
from setup.create_divisions import create_divisions
from setup.create_players import migrate_players
from setup.create_players import search_players
from setup.create_players import create_players_for_draft_year
from setup.create_player_data import create_player_seasons
from setup.create_player_data import create_player_data
from setup.create_player_data import create_player_contracts
from setup.create_player_data import create_player_drafts
from setup.create_player_data import create_capfriendly_ids
from setup.create_player_data import create_capfriendly_ids_by_team
from setup.create_player_data import create_latest_contract_signings

from utils import prepare_logging
prepare_logging(log_types=['file', 'screen'])


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Setup script for NHL database creation.')
    parser.add_argument(
        'steps', metavar='setup_steps', help='Setup steps to execute.',
        choices=[
            'a', 'c', 't', 'd', 'p', 'pf', 'pc',
            'ps', 'pd', 'cf', 'cft', 'dft', 'lc'])
    parser.add_argument(
        '--roster_src', dest='roster_src', action='store', default='roster',
        choices=['roster', 'system', 'contract'],
        help='source type for player search')
    parser.add_argument(
        '--draft_year', dest='draft_year', action='store', default=2017,
        help='draft year to retrieve players from')
    parser.add_argument(
        '--roster_season', dest='roster_season', action='store', default=None,
        help='season to retrieve roster players for')
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
    # finding players on roster/system/contract pages
    if setup_steps in ['pf', 'a']:
        search_players(args.roster_src, args.roster_season)
    # creating players from draft overview
    if setup_steps in ['pc', 'a']:
        create_players_for_draft_year(args.draft_year)
    # retrieving player season statistics for all players in database
    if setup_steps in ['ps', 'a']:
        create_player_seasons()
    # retrieving individual player data for all players in database
    if setup_steps in ['pd', 'a']:
        create_player_data()
    # retrieving contract data for all players in database
    if setup_steps in ['c']:
        create_player_contracts()
    # retrieving latest contract signings
    if setup_steps in ['lc']:
        create_latest_contract_signings(5)
    # retrieving draft data for all players in database
    if setup_steps in ['dft']:
        create_player_drafts()
    # retrieving capfriendly ids for all players in database
    if setup_steps in ['cf']:
        create_capfriendly_ids()
    # retrieving capfriendly ids for players of all teams in database
    if setup_steps in ['cft']:
        create_capfriendly_ids_by_team()
