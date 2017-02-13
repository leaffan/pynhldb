#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests

from db.team import Team


def test_find_by_abbr():
    t = Team.find('BOS')
    assert t.name == 'Boston Bruins'


def test_find_by_orig_abbr():
    t = Team.find('S.J')
    assert t.name == 'San Jose Sharks'


def test_find_by_name():
    t = Team.find_by_name('Vancouver Canucks')
    assert t.name == 'Vancouver Canucks'


def test_find_by_id():
    t = Team.find_by_id(1)
    assert t.name == 'New Jersey Devils'


def test_find_by_name_montreal():
    t = Team.find_by_name('Canadiens Montreal')
    assert t.name == 'Montréal Canadiens'


def test_find_by_name_oakland():
    t = Team.find_by_name('Oakland Seals')
    assert t.name == 'Oakland Seals'


def test_constructor():
    url = "https://statsapi.web.nhl.com/api/v1/teams/10"
    response = requests.get(url)
    raw_team_data = response.json()

    t = Team(raw_team_data['teams'][0])

    assert t.name == 'Toronto Maple Leafs'
    assert t.franchise_id == 5
    assert t.team_id == 10
    assert t.short_name == 'Toronto'
    assert t.team_name == 'Maple Leafs'
    assert t.abbr == 'TOR'
    assert t.first_year_of_play == '1917'


def test_comparison_operators():
    team_1 = Team.find_by_id(10)
    team_2 = Team.find_by_name("Toronto Maple Leafs")
    team_3 = Team.find_by_id(1)

    assert team_1 == team_2
    assert team_1 != team_3
    assert team_1 > team_3
    assert team_3 < team_1
