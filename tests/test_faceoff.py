#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .test_event import get_event_parser


def test_faceoff(download_summaries):

    game_id = "020001"
    event_idx = 1

    dld_dir = download_summaries.get_tgt_dir()

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
