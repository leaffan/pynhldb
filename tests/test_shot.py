#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lxml import html
import tempfile

from utils.summary_downloader import SummaryDownloader
from utils.data_handler import DataHandler
from parsers.team_parser import TeamParser
from parsers.game_parser import GameParser
from parsers.roster_parser import RosterParser
from parsers.event_parser import EventParser

TMP_DIR = tempfile.mkdtemp(prefix='shot_test_')


def setup_game_teams_rosters():

    date = "Oct 12, 2016"
    game_id = "020001"

    sdl = SummaryDownloader(TMP_DIR, date, zip_summaries=False)
    sdl.run()
    dld_dir = sdl.get_tgt_dir()

    game_report_doc = html.fromstring(get_document(dld_dir, game_id, 'GS'))
    roster_report_doc = html.fromstring(get_document(dld_dir, game_id, 'ES'))
    play_by_play_report_doc = html.fromstring(
        get_document(dld_dir, game_id, 'PL'))
    game_feed_json_doc = get_json_document(dld_dir, game_id)

    tp = TeamParser(game_report_doc)
    teams = tp.create_teams()
    gp = GameParser(game_id, game_report_doc)
    game = gp.create_game(teams)
    rp = RosterParser(roster_report_doc)
    rosters = rp.create_roster(game, teams)
    ep = EventParser(play_by_play_report_doc, game_feed_json_doc)
    ep.load_data()
    (ep.game, ep.rosters) = (game, rosters)
#     event_data_item = ep.event_data[7]
#     event = ep.get_event(event_data_item)
#     shot = ep.specify_event(event)
#     assert shot.team_id == 12


def get_document(dir, game_id, prefix):
    dh = DataHandler(dir)
    return dh.get_game_data(game_id, prefix)


def get_json_document(dir, game_id):
    dh = DataHandler(dir)
    return dh.get_game_json_data(game_id)
