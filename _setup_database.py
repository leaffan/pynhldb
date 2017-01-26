#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setup.create_teams import migrate_teams
from setup.create_divisions import create_divisions
from setup.create_players import migrate_players
from setup.create_player_seasons import create_player_seasons
from setup.create_player_seasons import create_player_data

from utils import prepare_logging
prepare_logging(log_types=['file', 'screen'])


if __name__ == '__main__':

    # migrating teams from json file to database
    migrate_teams(simulation=True)
    # creating divisions from division configuration file
    create_divisions(simulation=True)
    # migrating players from json file to database
    migrate_players(simulation=True)
    # retrieving player season statistics for all players in database
    create_player_seasons(simulation=False)
    # retrieving individual player data for all players in database
    create_player_data(simulation=False)