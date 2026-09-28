#!/usr/bin/env python

import os
from datetime import date, datetime, time

import dateutil
import pytest
import requests
from lxml import html

from parsers.game_parser import GameParser
from parsers.team_parser import TeamParser


def test_2016():

    url = "http://www.nhl.com/scores/htmlreports/20162017/GS020776.HTM"
    gp = prepare_game_parser(url)

    game_data = {}

    game_data = gp.retrieve_standard_game_data(game_data)
    assert game_data['date'] == date(2017, 2, 4)
    assert game_data['season'] == 2016
    assert game_data['game_id'] == 2016020776
    assert game_data['type'] == 2
    # last modification date is only added to downloaded and archived data
    assert game_data['data_last_modified'] is None

    game_data['attendance'], game_data['venue'] = gp.retrieve_game_attendance_venue()
    assert game_data['attendance'] == 19092
    assert game_data['venue'] == "Amalie Arena"

    game_data['start'], game_data['end'] = gp.retrieve_game_start_end(game_data['date'], game_data['type'])
    assert game_data['start'] == datetime.combine(
        game_data['date'], time(19, 8, 0, 0, tzinfo=dateutil.tz.tzoffset('EST', -18000)))
    assert game_data['end'] == datetime.combine(
        game_data['date'], time(22, 9, 0, 0, tzinfo=dateutil.tz.tzoffset('EST', -18000)))

    game_data['overtime_game'], game_data['shootout_game'] = gp.retrieve_overtime_shootout_information(
        game_data['type'])
    assert game_data['overtime_game'] is True
    assert game_data['shootout_game'] is True

    # TODO: test teams in game


def test_playoff_game():

    url = "http://www.nhl.com/scores/htmlreports/20122013/GS030325.HTM"
    gp = prepare_game_parser(url)

    game_data = {}

    game_data = gp.retrieve_standard_game_data(game_data)
    assert game_data['date'] == date(2013, 6, 8)
    assert game_data['season'] == 2012
    assert game_data['game_id'] == 2012030325
    assert game_data['type'] == 3
    # last modification date is only added to downloaded and archived data
    assert game_data['data_last_modified'] is None

    game_data['attendance'], game_data['venue'] = gp.retrieve_game_attendance_venue()
    assert game_data['attendance'] == 22237
    assert game_data['venue'] == "United Center"

    game_data['start'], game_data['end'] = gp.retrieve_game_start_end(game_data['date'], game_data['type'])
    assert game_data['start'] == datetime.combine(
        game_data['date'], time(19, 20, 0, 0, tzinfo=dateutil.tz.tzoffset('CDT', -18000)))
    assert game_data['end'] == datetime.combine(
        game_data['date'], time(23, 2, 0, 0, tzinfo=dateutil.tz.tzoffset('CDT', -18000)))

    game_data['overtime_game'], game_data['shootout_game'] = gp.retrieve_overtime_shootout_information(
        game_data['type'])
    assert game_data['overtime_game'] is True
    assert game_data['shootout_game'] is False

    # TODO: test teams in game


def test_bilingual():

    url = "http://www.nhl.com/scores/htmlreports/20112012/GS020256.HTM"
    gp = prepare_game_parser(url)

    game_data = {}

    game_data = gp.retrieve_standard_game_data(game_data)
    assert game_data['date'] == date(2011, 11, 16)
    assert game_data['season'] == 2011
    assert game_data['game_id'] == 2011020256
    assert game_data['type'] == 2
    # last modification date is only added to downloaded and archived data
    assert game_data['data_last_modified'] is None

    game_data['attendance'], game_data['venue'] = gp.retrieve_game_attendance_venue()
    assert game_data['attendance'] == 21273
    assert game_data['venue'] == "Centre Bell"

    game_data['start'], game_data['end'] = gp.retrieve_game_start_end(game_data['date'], game_data['type'])
    assert game_data['start'] == datetime.combine(
        game_data['date'], time(19, 10, 0, 0, tzinfo=dateutil.tz.tzoffset('EST', -18000)))
    assert game_data['end'] == datetime.combine(
        game_data['date'], time(21, 30, 0, 0, tzinfo=dateutil.tz.tzoffset('EST', -18000)))

    game_data['overtime_game'], game_data['shootout_game'] = gp.retrieve_overtime_shootout_information(
        game_data['type'])
    assert game_data['overtime_game'] is False
    assert game_data['shootout_game'] is False

    # TODO: test teams in game


def test_shootout_report_present_but_unused_for_overtime_game():
    # 2025020157 (Oct 28, 2025) was decided in overtime, not a shootout.
    # The SO report is downloaded for every game regardless of whether it
    # actually went to a shootout, so its mere presence must not be taken
    # as evidence that a shootout happened.
    gs_url = "http://www.nhl.com/scores/htmlreports/20252026/GS020157.HTM"
    gp = prepare_game_parser(gs_url)

    game_data = gp.retrieve_standard_game_data({})
    overtime_game, shootout_game = gp.retrieve_overtime_shootout_information(game_data['type'])
    assert overtime_game is True
    assert shootout_game is False

    # for a game that didn't go to a shootout, the SO report has no
    # shootout summary table, so parsing it unconditionally raises - this
    # is exactly why create_team_games()/retrieve_shootout_information()
    # must gate on shootout_game rather than "SO data is not None"
    so_data = get_data("http://www.nhl.com/scores/htmlreports/20252026/SO020157.HTM")
    with pytest.raises(IndexError):
        gp.retrieve_shootout_attempts({'home_road_type': 'home'}, so_data)


def test_shootout_attempts_for_actual_shootout_game():
    # 2016020776 (see test_2016 above) did go to a shootout
    gp = prepare_game_parser("http://www.nhl.com/scores/htmlreports/20162017/GS020776.HTM")
    so_data = get_data("http://www.nhl.com/scores/htmlreports/20162017/SO020776.HTM")

    home_team_game_data = gp.retrieve_shootout_attempts({'home_road_type': 'home'}, so_data)
    road_team_game_data = gp.retrieve_shootout_attempts({'home_road_type': 'road'}, so_data)

    assert home_team_game_data['so_goals'] == 3
    assert home_team_game_data['so_attempts'] == 4
    assert road_team_game_data['so_goals'] == 2
    assert road_team_game_data['so_attempts'] == 4


def prepare_game_parser(url):
    game_id = str(os.path.splitext(os.path.basename(url))[0][2:])
    gp = GameParser(game_id, get_data(url))
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
