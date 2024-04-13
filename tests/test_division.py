#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import date
from operator import itemgetter, attrgetter
from collections import defaultdict


import requests

from db.team import Team
from db.division import Division


def test_division_import():
    """
    Tests whether team abbreviations used in division configuration file
    correspond with team abbreviations used by team definitions in database.
    """
    div_src = os.path.join(os.path.dirname(__file__), 'test_division_config.txt')
    lines = [line.strip() for line in open(div_src).readlines()]

    team_abbs = set()

    for line in lines:
        if line.startswith('#'):
            continue
        tokens = line.split(';')
        raw_abbs = tokens[2][1:-1].split(',')
        for raw_abb in raw_abbs:
            team_abbs.add(raw_abb)

    for abb in sorted(team_abbs):
        t = Team.find(abb)
        assert abb in [t.abbr, t.orig_abbr]


def test_division_1974():
    """
    Tests divisions stored in database for 1974/75 season.
    """
    divisions = Division.get_divisions_and_teams(1974)

    assert sorted(divisions.keys()) == ['Adams', 'Norris', 'Patrick', 'Smythe']
    assert [t.name for t in divisions['Adams']] == [
        'Boston Bruins',
        'Buffalo Sabres',
        'California Golden Seals',
        'Toronto Maple Leafs']
    assert [t.name for t in divisions['Norris']] == [
        'Detroit Red Wings',
        'Los Angeles Kings',
        'Montréal Canadiens',
        'Pittsburgh Penguins',
        'Washington Capitals']
    assert [t.name for t in divisions['Patrick']] == [
        'Atlanta Flames',
        'New York Islanders',
        'New York Rangers',
        'Philadelphia Flyers']
    assert [t.name for t in divisions['Smythe']] == [
        'Chicago Blackhawks',
        'Kansas City Scouts',
        'Minnesota North Stars',
        'St. Louis Blues',
        'Vancouver Canucks']


def test_division_now():
    """
    Tests whether current divisions in database correspond to the ones used by the NHL web api.
    """
    # retrieving current divisions and teams from database
    divisions_from_db = Division.get_divisions_and_teams()

    # urls for current standings to get current divisions and teams
    standings_url = f"https://api-web.nhle.com/v1/standings/{date.today()}"
    response = requests.get(standings_url)
    standings = response.json()['standings']

    # getting all available divisions from standings
    divisions_from_url = sorted(list(set(map(itemgetter('divisionName'), standings))))

    teams_by_division_from_url = defaultdict(list)

    for division in divisions_from_url:
        # getting teams in current division from standings
        teams_in_division = list(filter(lambda t, division=division: t['divisionName'] == division, standings))
        teams_in_division = list(map(itemgetter('teamName'), teams_in_division))
        teams_in_division = sorted(list(map(itemgetter('default'), teams_in_division)))
        teams_by_division_from_url[division] = teams_in_division

    assert sorted(divisions_from_db.keys()) == sorted(divisions_from_url)

    for division in divisions_from_db:
        teams_from_db = map(attrgetter('name'), divisions_from_db[division])
        assert sorted(teams_from_db) == sorted(teams_by_division_from_url[division])
