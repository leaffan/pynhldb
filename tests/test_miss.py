#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import distinct

from db.miss import Miss
from db.common import session_scope

from .test_event import get_event_parser

from tests import VALID_SHOT_TYPES
from tests import VALID_ZONES


def test_miss(download_summaries):

    game_id = "020001"
    event_idx = 9

    dld_dir = download_summaries.get_tgt_dir()

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


def test_miss_shot_type():
    """
    Tests all existing shot types in database for their validity.
    """
    with session_scope() as session:
        all_shot_types = session.query(distinct(Miss.shot_type)).all()
        all_shot_types = [shot_type for (shot_type,) in all_shot_types]
        for shot_type in all_shot_types:
            # null is an acceptable shot type, too
            if shot_type is None:
                continue
            assert shot_type in VALID_SHOT_TYPES


def test_miss_zone():
    """
    Tests all existing shot zones in database for their validity.
    """
    with session_scope() as session:
        all_shot_zones = session.query(distinct(Miss.zone)).all()
        all_shot_zones = [shot_zone for (shot_zone,) in all_shot_zones]
        for shot_zone in all_shot_zones:
            assert shot_zone in VALID_ZONES
