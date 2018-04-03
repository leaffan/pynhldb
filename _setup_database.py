#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from setup import create_teams as ct
from setup import create_divisions as cd
from setup import create_players as cp
from setup import create_player_data as cpd

from utils import prepare_logging
prepare_logging(log_types=['file', 'screen'])


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Setup script for NHL database creation.')
    parser.add_argument(
        'steps', metavar='setup_steps', help='Setup steps to execute.',
        choices=[
            'a', 'c', 't', 'd', 'p', 'pf', 'pc',
            'ps', 'pd', 'cf', 'cft', 'dft', 'lc', 'ct'])
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
    parser.add_argument(
        '--roster_teams', dest='roster_teams', nargs='+', action='store',
        default=None, help='teams to retrieve roster players for')
    parser.add_argument(
        '--contract_count', dest='contract_count', action='store',
        type=int, default=5, help='number of latest signings to retrieve')
    args = parser.parse_args()
    setup_steps = args.steps

    # migrating teams from json file to database
    if setup_steps in ['t', 'a']:
        ct.migrate_teams()
    # creating divisions from division configuration file
    if setup_steps in ['d', 'a']:
        cd.create_divisions()
    # migrating players from json file to database
    if setup_steps in ['p', 'a']:
        cp.migrate_players()
    # finding players on roster/system/contract pages
    if setup_steps in ['pf', 'a']:
        cp.search_players(
            args.roster_src, args.roster_teams, args.roster_season)
    # creating players from draft overview
    if setup_steps in ['pc', 'a']:
        cp.create_players_for_draft_year(args.draft_year)
    # retrieving player season statistics for all players in database
    if setup_steps in ['ps', 'a']:
        cpd.create_player_seasons()
    # retrieving individual player data for all players in database
    if setup_steps in ['pd', 'a']:
        cpd.create_player_data()
    # retrieving contract data for all players in database
    if setup_steps in ['c']:
        cpd.create_player_contracts()
    # retrieving contract data for all players contracted
    if setup_steps in ['ct']:
        cpd.create_player_contracts_by_team()
    # retrieving latest contract signings
    if setup_steps in ['lc']:
        cpd.create_latest_contract_signings(args.contract_count)
    # retrieving draft data for all players in database
    if setup_steps in ['dft']:
        cpd.create_player_drafts()
    # retrieving capfriendly ids for all players in database
    if setup_steps in ['cf']:
        cpd.create_capfriendly_ids()
    # retrieving capfriendly ids for players of all teams in database
    if setup_steps in ['cft']:
        cpd.create_capfriendly_ids_by_team()
