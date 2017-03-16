#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import requests
from lxml import html

from parsers.team_parser import TeamParser
from parsers.game_parser import GameParser


def test_2016():

    url = "http://www.nhl.com/scores/htmlreports/20162017/ES020776.HTM"

    game_id = str(os.path.splitext(os.path.basename(url))[0][2:])

    tp = TeamParser(get_data(url))
    tp.load_data()
    tp.create_teams()

    gp = GameParser(game_id, get_data(url), None)
    gp.load_data()
    gp.create_game(tp.teams)

    assert gp.game_data == [
        'Saturday, February 4, 2017', 'Attendance 19,092 at Amalie Arena',
        'Start 7:08 EST; End 10:09 EST', 'Game 0776', 'Final']


def test_playoff_game():

    url = "http://www.nhl.com/scores/htmlreports/20122013/GS030325.HTM"

    game_id = str(os.path.splitext(os.path.basename(url))[0][2:])

    tp = TeamParser(get_data(url))
    tp.load_data()
    tp.create_teams()

    gp = GameParser(game_id, get_data(url), None)
    gp.load_data()
    gp.create_game(tp.teams)

    assert gp.game_data == [
        'Saturday, June 8, 2013', 'Attendance 22,237 at United Center',
        'Start 7:20 CDT; End 11:02 CDT', 'Game 0325', 'Final']


def test_2013_centre_bell():

    url = "http://www.nhl.com/scores/htmlreports/20132014/ES020001.HTM"

    game_id = str(os.path.splitext(os.path.basename(url))[0][2:])

    gp = GameParser(game_id, get_data(url))
    gp.load_data()
    attendance, venue = gp.retrieve_game_attendance_venue()
    assert attendance == 21273
    assert venue == "Centre Bell"


def get_data(url):
    r = requests.get(url)
    return html.fromstring(r.text)
