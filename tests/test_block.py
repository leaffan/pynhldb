#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils.summary_downloader import SummaryDownloader
from .test_event import get_event_parser


def test_block(tmpdir):

    date = "Oct 12, 2016"
    game_id = "020001"
    event_idx = 5

    sdl = SummaryDownloader(
        tmpdir.mkdir('block').strpath, date, zip_summaries=False)
    sdl.run()
    dld_dir = sdl.get_tgt_dir()

    ep = get_event_parser(dld_dir, game_id)
    event = ep.get_event(ep.event_data[event_idx])
    block = ep.specify_event(event)

    assert block.event_id == event.event_id
    assert block.team_id == 9
    assert block.blocked_team_id == 10
    assert block.player_id == 8475913
    assert block.blocked_player_id == 8474581
    assert block.shot_type == 'Slap'
    assert block.zone == 'Def'
    # assert shot.goalie_id == 8467950
    # assert shot.goalie_team_id == 9
    # assert not shot.scored

    tmpdir.remove()
