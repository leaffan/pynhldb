#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from lxml import html

from parsers.team_parser import TeamParser

# TODO: add further tests


def test_2016():

    url = "http://www.nhl.com/scores/htmlreports/20162017/ES020776.HTM"

    tp = TeamParser(get_data(url))
    tp.load_data()

    assert [s for s in tp.team_data['road'] if s.strip()] == [
        'VISITOR', 'ANAHEIM DUCKS', 'Game 54 Away Game 28', '2']
    assert [s for s in tp.team_data['home'] if s.strip()] == [
        'HOME', 'TAMPA BAY LIGHTNING', 'Game 53 Home Game 25', '3']

    tp.create_teams()

    assert tp.teams['road'].name == "Anaheim Ducks"
    assert tp.teams['home'].name == "Tampa Bay Lightning"
    assert tp.teams['road'].game_no == 54
    assert tp.teams['home'].game_no == 53
    assert tp.teams['road'].home_road_no == 28
    assert tp.teams['home'].home_road_no == 25
    assert tp.teams['road'].score == 2
    assert tp.teams['home'].score == 3


def test_2001_canadien():

    url = "http://www.nhl.com/scores/htmlreports/20012002/ES020781.HTM"

    tp = TeamParser(get_data(url))
    tp.load_data()

    assert [s for s in tp.team_data['road'] if s.strip()] == [
        'SAN JOSE SHARKS', 'M/G 51 Étr. / Away 27', '1']
    assert [s for s in tp.team_data['home'] if s.strip()] == [
        'CANADIEN DE MONTREAL', 'M/G 53 Dom. / Home 25', '3']

    tp.create_teams()

    assert tp.teams['road'].name == "San Jose Sharks"
    assert tp.teams['home'].name == "Montréal Canadiens"
    assert tp.teams['road'].game_no == 51
    assert tp.teams['home'].game_no == 53
    assert tp.teams['road'].home_road_no == 27
    assert tp.teams['home'].home_road_no == 25
    assert tp.teams['road'].score == 1
    assert tp.teams['home'].score == 3


def test_2001_atlanta_phoenix():

    url = "http://www.nhl.com/scores/htmlreports/20012002/ES020785.HTM"

    tp = TeamParser(get_data(url))
    tp.load_data()

    assert [s for s in tp.team_data['road'] if s.strip()] == [
        'VISITOR', 'PHOENIX COYOTES', 'Game 52 Away Game 27', '4']
    assert [s for s in tp.team_data['home'] if s.strip()] == [
        'HOME', 'ATLANTA THRASHERS', 'Game 53 Home Game 26', '2']

    tp.create_teams()

    assert tp.teams['road'].name == "Phoenix Coyotes"
    assert tp.teams['home'].name == "Atlanta Thrashers"
    assert tp.teams['road'].game_no == 52
    assert tp.teams['home'].game_no == 53
    assert tp.teams['road'].home_road_no == 27
    assert tp.teams['home'].home_road_no == 26
    assert tp.teams['road'].score == 4
    assert tp.teams['home'].score == 2


def get_data(url):
    r = requests.get(url)
    return html.fromstring(r.text)
