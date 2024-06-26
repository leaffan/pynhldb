#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime

import json
from lxml import html

from db.common import session_scope
from db.event import Event

from utils.data_handler import DataHandler
from parsers.team_parser import TeamParser
from parsers.game_parser import GameParser
from parsers.roster_parser import RosterParser
from parsers.event_parser import EventParser


def test_event(download_summaries):

    game_id = "020001"

    dld_dir = download_summaries.get_tgt_dir()

    ep = get_event_parser(dld_dir, game_id)
    event = ep.get_event(ep.event_data[1])

    assert event.event_id == 20160200010002
    assert event.game_id == 2016020001
    assert event.in_game_event_cnt == 2
    assert event.type == 'FAC'
    assert event.period == 1
    assert event.time == datetime.timedelta(0)
    assert event.road_on_ice == [8475172, 8473463, 8470599, 8476853, 8475716, 8475883]
    assert event.home_on_ice == [8474250, 8473544, 8471676, 8470602, 8476879, 8467950]
    assert event.road_score == 0
    assert event.home_score == 0
    assert event.x == 0
    assert event.y == 0
    assert event.road_goalie == 8475883
    assert event.home_goalie == 8467950
    assert event.raw_data == ("TOR won Neu. Zone - TOR #43 KADRI vs OTT #19 BRASSARD")


def get_document(dir, game_id, prefix):
    dh = DataHandler(dir)
    return open(dh.get_game_data(game_id, prefix)[prefix]).read()


def get_json_document(dir, game_id):
    dh = DataHandler(dir)
    return json.loads(open(dh.get_game_json_data(game_id)).read())


def get_event_parser(dir, game_id):
    """
    Retrieves event parser for game with specified id from
    data downloaded to directory also given.
    """
    # retrieving raw data
    game_report_doc = html.fromstring(get_document(dir, game_id, 'GS'))
    event_summary_doc = html.fromstring(get_document(dir, game_id, 'ES'))
    roster_report_doc = html.fromstring(get_document(dir, game_id, 'RO'))
    play_by_play_report_doc = html.fromstring(get_document(dir, game_id, 'PL'))
    game_feed_json_doc = get_json_document(dir, game_id)

    # using team parser to retrieve teams
    tp = TeamParser(game_report_doc)
    teams = tp.create_teams()
    # using game parser to retrieve basic game information
    gp = GameParser(game_id, game_report_doc)
    game = gp.create_game(teams, False)
    # using roster parser to retrieve team rosters
    rp = RosterParser(event_summary_doc)
    rosters = rp.create_roster(game, teams, roster_report_doc)

    # using event parser to retrieve all raw events
    ep = EventParser(play_by_play_report_doc, game_feed_json_doc, game_report_doc)
    ep.load_data()
    (ep.game, ep.rosters) = (game, rosters)
    ep.cache_plays_with_coordinates()
    return ep


def test_event_types_not_being_null():
    """
    Tests whether there are events in the database with a null type.
    """
    with session_scope() as session:
        null_type_events = session.query(Event).filter(Event.type.is_(None)).all()
        assert not null_type_events
