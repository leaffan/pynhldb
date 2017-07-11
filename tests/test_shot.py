#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from lxml import html
import tempfile

from utils.summary_downloader import SummaryDownloader
from utils.data_handler import DataHandler
from parsers.team_parser import TeamParser
from parsers.game_parser import GameParser
from parsers.roster_parser import RosterParser
from parsers.event_parser import EventParser

TMP_DIR = tempfile.mkdtemp(prefix='shot_test_')


def test_shot():

    date = "Oct 12, 2016"
    game_id = "020001"

    sdl = SummaryDownloader(TMP_DIR, date, zip_summaries=False)
    sdl.run()
    dld_dir = sdl.get_tgt_dir()

    ep = get_event_parser(dld_dir, game_id)
    event = ep.get_event(ep.event_data[7])
    shot = ep.specify_event(event)

    assert shot.event_id == event.event_id
    assert shot.team_id == 10
    assert shot.player_id == 8478483
    assert shot.shot_type == 'Wrist'
    assert shot.distance == 13
    assert shot.zone == 'Off'
    assert shot.goalie_id == 8467950
    assert shot.goalie_team_id == 9
    assert not shot.scored


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
    roster_report_doc = html.fromstring(get_document(dir, game_id, 'ES'))
    play_by_play_report_doc = html.fromstring(
        get_document(dir, game_id, 'PL'))
    game_feed_json_doc = get_json_document(dir, game_id)

    # using team parser to retrieve teams
    tp = TeamParser(game_report_doc)
    teams = tp.create_teams()
    # using game parser to retrieve basic game information
    gp = GameParser(game_id, game_report_doc)
    game = gp.create_game(teams)
    # using roster parser to retrieve team rosters
    rp = RosterParser(roster_report_doc)
    rosters = rp.create_roster(game, teams)

    # using event parser to retrieve all raw events
    ep = EventParser(play_by_play_report_doc, game_feed_json_doc)
    ep.load_data()
    (ep.game, ep.rosters) = (game, rosters)
    ep.cache_plays_with_coordinates()
    return ep
