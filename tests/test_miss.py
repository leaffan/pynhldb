#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils.summary_downloader import SummaryDownloader
from .test_event import get_event_parser


def test_miss(tmpdir):

    date = "Oct 12, 2016"
    game_id = "020001"
    event_idx = 9

    sdl = SummaryDownloader(
        tmpdir.mkdir('miss').strpath, date, zip_summaries=False)
    sdl.run()
    dld_dir = sdl.get_tgt_dir()

    ep = get_event_parser(dld_dir, game_id)
    event = ep.get_event(ep.event_data[event_idx])
    miss = ep.specify_event(event)

    assert miss.event_id == event.event_id
    assert miss.team_id == 9
    assert miss.player_id == 8470602
    assert miss.shot_type == 'Wrist'
    assert miss.zone == 'Off'
    assert miss.goalie_team_id == 10
    assert miss.goalie_id == 8475883
    assert miss.miss_type == 'Wide of Net'
    assert miss.shot_type == 'Wrist'
    assert not miss.penalty_shot
    # assert shot.goalie_id == 8467950
    # assert shot.goalie_team_id == 9
    # assert not shot.scored

    tmpdir.remove()
