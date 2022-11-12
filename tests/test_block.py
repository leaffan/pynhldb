#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import distinct

from db.common import session_scope
from db.block import Block

from utils.summary_downloader import SummaryDownloader
from .test_event import get_event_parser

from tests import VALID_SHOT_TYPES
from tests import VALID_ZONES


def test_block(tmpdir):

    date = "Oct 12, 2016"
    game_id = "020001"
    event_idx = 5

    sdl = SummaryDownloader(
        tmpdir.mkdir('block').strpath, date,
        zip_summaries=False, cleanup=False)
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


def test_blocked_shot_type():
    """
    Tests all existing blocked shot types in database for their validity.
    """
    with session_scope() as session:
        all_shot_types = session.query(distinct(Block.shot_type)).all()
        all_shot_types = [shot_type for (shot_type,) in all_shot_types]
        for shot_type in all_shot_types:
            # null is an acceptable shot type, too
            if shot_type is None:
                continue
            assert shot_type in VALID_SHOT_TYPES


def test_blocked_shot_zone():
    """
    Tests all existing blocked shot zones in database for their validity.
    """
    with session_scope() as session:
        all_shot_zones = session.query(distinct(Block.zone)).all()
        all_shot_zones = [shot_zone for (shot_zone,) in all_shot_zones]
        for shot_zone in all_shot_zones:
            # null is an acceptable zone for a blocked shot, too
            if shot_zone is None:
                continue
            assert shot_zone in VALID_ZONES
