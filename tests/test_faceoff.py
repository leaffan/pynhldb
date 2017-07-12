#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils.summary_downloader import SummaryDownloader
from .test_event import get_event_parser


def test_faceoff(tmpdir):

    date = "Oct 12, 2016"
    game_id = "020001"
    event_idx = 1

    sdl = SummaryDownloader(
        tmpdir.mkdir('faceoff').strpath, date, zip_summaries=False)
    sdl.run()
    dld_dir = sdl.get_tgt_dir()

    ep = get_event_parser(dld_dir, game_id)
    event = ep.get_event(ep.event_data[event_idx])
    faceoff = ep.specify_event(event)

    assert faceoff.event_id == event.event_id
    assert faceoff.zone == 'Neu'
    assert faceoff.faceoff_lost_zone == 'Neu'
    assert faceoff.team_id == 10
    assert faceoff.faceoff_lost_team_id == 9
    assert faceoff.player_id == 8475172
    assert faceoff.faceoff_lost_player_id == 8473544

    tmpdir.remove()
