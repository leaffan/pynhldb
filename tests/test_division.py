#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from collections import defaultdict

import requests

from db.team import Team
from db.division import Division


def test_division_import():
    """
    Tests whether team abbreviations used in division configuration file
    correspond with team abbreviations used by team definitions in database.
    """
    div_src = os.path.join(
        os.path.dirname(__file__), 'test_division_config.txt')
    lines = [l.strip() for l in open(div_src).readlines()]

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

    # retrieving current divisions and teams from database
    divisions_from_db = Division.get_divisions_and_teams()

    # urls with current division and team data
    divisions_url = "https://statsapi.web.nhl.com/api/v1/divisions/"
    teams_url = "https://statsapi.web.nhl.com/api/v1/teams/"

    response = requests.get(divisions_url)
    divisions_from_url = [d['name'] for d in response.json()['divisions']]

    response = requests.get(teams_url)
    teams_by_division_from_url = defaultdict(list)
    for team_json in response.json()['teams']:
        team_name = team_json['name']
        team_division = team_json['division']['name']
        teams_by_division_from_url[team_division].append(team_name)

    assert sorted(divisions_from_db.keys()) == sorted(divisions_from_url)

    for division in divisions_from_db:
        assert sorted(
            [t.name for t in divisions_from_db[division]]
        ) == sorted(
            teams_by_division_from_url[division]
        )
