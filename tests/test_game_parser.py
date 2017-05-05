#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import date, time, datetime

import requests
import dateutil
from lxml import html

from parsers.team_parser import TeamParser
from parsers.game_parser import GameParser


def test_2016():

    url = "http://www.nhl.com/scores/htmlreports/20162017/GS020776.HTM"
    gp = prepare_game_parser(url)

    game_data = dict()

    game_data = gp.retrieve_standard_game_data(game_data)
    assert game_data['date'] == date(2017, 2, 4)
    assert game_data['season'] == 2016
    assert game_data['game_id'] == 2016020776
    assert game_data['type'] == 2
    # last modification date is only added to downloaded and archived data
    assert game_data['data_last_modified'] is None

    (
        game_data['attendance'],
        game_data['venue']) = gp.retrieve_game_attendance_venue()
    assert game_data['attendance'] == 19092
    assert game_data['venue'] == "Amalie Arena"

    game_data['start'], game_data['end'] = gp.retrieve_game_start_end(
        game_data['date'], game_data['type'])
    assert game_data['start'] == datetime.combine(
        game_data['date'], time(19, 8, 0, 0, tzinfo=dateutil.tz.tzoffset(
            'EST', -18000)))
    assert game_data['end'] == datetime.combine(
        game_data['date'], time(22, 9, 0, 0, tzinfo=dateutil.tz.tzoffset(
            'EST', -18000)))

    (
        game_data['overtime_game'],
        game_data['shootout_game']
    ) = gp.retrieve_overtime_shootout_information(game_data['type'])
    assert game_data['overtime_game'] is True
    assert game_data['shootout_game'] is True

    # TODO: test teams in game


def test_playoff_game():

    url = "http://www.nhl.com/scores/htmlreports/20122013/GS030325.HTM"
    gp = prepare_game_parser(url)

    game_data = dict()

    game_data = gp.retrieve_standard_game_data(game_data)
    assert game_data['date'] == date(2013, 6, 8)
    assert game_data['season'] == 2012
    assert game_data['game_id'] == 2012030325
    assert game_data['type'] == 3
    # last modification date is only added to downloaded and archived data
    assert game_data['data_last_modified'] is None

    (
        game_data['attendance'],
        game_data['venue']) = gp.retrieve_game_attendance_venue()
    assert game_data['attendance'] == 22237
    assert game_data['venue'] == "United Center"

    game_data['start'], game_data['end'] = gp.retrieve_game_start_end(
        game_data['date'], game_data['type'])
    assert game_data['start'] == datetime.combine(
        game_data['date'], time(19, 20, 0, 0, tzinfo=dateutil.tz.tzoffset(
            'CDT', -18000)))
    assert game_data['end'] == datetime.combine(
        game_data['date'], time(23, 2, 0, 0, tzinfo=dateutil.tz.tzoffset(
            'CDT', -18000)))

    (
        game_data['overtime_game'],
        game_data['shootout_game']
    ) = gp.retrieve_overtime_shootout_information(game_data['type'])
    assert game_data['overtime_game'] is True
    assert game_data['shootout_game'] is False

    # TODO: test teams in game


def test_bilingual():

    url = "http://www.nhl.com/scores/htmlreports/20112012/GS020256.HTM"
    gp = prepare_game_parser(url)

    game_data = dict()

    game_data = gp.retrieve_standard_game_data(game_data)
    assert game_data['date'] == date(2011, 11, 16)
    assert game_data['season'] == 2011
    assert game_data['game_id'] == 2011020256
    assert game_data['type'] == 2
    # last modification date is only added to downloaded and archived data
    assert game_data['data_last_modified'] is None

    (
        game_data['attendance'],
        game_data['venue']) = gp.retrieve_game_attendance_venue()
    assert game_data['attendance'] == 21273
    assert game_data['venue'] == "Centre Bell"

    game_data['start'], game_data['end'] = gp.retrieve_game_start_end(
        game_data['date'], game_data['type'])
    assert game_data['start'] == datetime.combine(
        game_data['date'], time(19, 10, 0, 0, tzinfo=dateutil.tz.tzoffset(
            'EST', -18000)))
    assert game_data['end'] == datetime.combine(
        game_data['date'], time(21, 30, 0, 0, tzinfo=dateutil.tz.tzoffset(
            'EST', -18000)))

    (
        game_data['overtime_game'],
        game_data['shootout_game']
    ) = gp.retrieve_overtime_shootout_information(game_data['type'])
    assert game_data['overtime_game'] is False
    assert game_data['shootout_game'] is False

    # TODO: test teams in game


def prepare_game_parser(url):
    game_id = str(os.path.splitext(os.path.basename(url))[0][2:])
    gp = GameParser(game_id, get_data(url), None)
    gp.load_data()

    return gp


def prepare_team_parser_and_teams(url):
    tp = TeamParser(get_data(url))
    tp.load_data()
    tp.create_teams()
    return tp.teams


def get_data(url):
    r = requests.get(url)
    return html.fromstring(r.text)
