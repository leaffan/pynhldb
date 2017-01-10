#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setup.create_teams import migrate_teams
from setup.create_divisions import create_divisions


if __name__ == '__main__':
    # migrating teams from json file to database
    migrate_teams(simulation=True)
    # creating divisions from division configuration file
    create_divisions(simulation=True)
