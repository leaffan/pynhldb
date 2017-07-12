#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils.summary_downloader import SummaryDownloader
from test_event import get_event_parser


def test_shot(tmpdir):

    date = "Oct 12, 2016"
    game_id = "020001"
    event_idx = 7

    sdl = SummaryDownloader(
        tmpdir.mkdir('shot').strpath, date, zip_summaries=False)
    sdl.run()
    dld_dir = sdl.get_tgt_dir()

    ep = get_event_parser(dld_dir, game_id)
    event = ep.get_event(ep.event_data[event_idx])
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

    tmpdir.remove()
