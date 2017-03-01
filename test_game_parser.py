#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from lxml import html

from parsers.team_parser import TeamParser
from parsers.game_parser import GameParser


def test_2016():

    url = "http://www.nhl.com/scores/htmlreports/20162017/ES020776.HTM"

    tp = TeamParser(get_data(url))
    tp.load_data()
    tp.create_teams()

    gp = GameParser(get_data(url), None)
    gp.load_data()
    gp.create_game(tp.teams)

    assert gp.game_data == [
        'Saturday, February 4, 2017', 'Attendance 19,092 at Amalie Arena',
        'Start 7:08 EST; End 10:09 EST', 'Game 0776', 'Final']


def test_playoff_game():

    url = "http://www.nhl.com/scores/htmlreports/20122013/ES030325.HTM"

    tp = TeamParser(get_data(url))
    tp.load_data()
    tp.create_teams()

    gp = GameParser(2, get_data(url), None)
    gp.load_data()
    gp.create_game(tp.teams)

    assert gp.game_data == [
        'Saturday, June 8, 2013', 'Attendance 22,237 at United Center',
        'Start 7:20 CDT; End 11:02 CDT', 'Game 0325', 'Final']


def get_data(url):
    r = requests.get(url)
    return html.fromstring(r.text)


if __name__ == '__main__':

    test_2016()
    test_playoff_game()
