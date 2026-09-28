#!/usr/bin/env python

from types import SimpleNamespace
from unittest.mock import patch

from parsers.event_parser import EventParser


def make_event_parser(game_id=999, home_team_id=111, road_team_id=222, score_diff=0):
    ep = EventParser.__new__(EventParser)
    ep.game = SimpleNamespace(
        game_id=game_id, home_team_id=home_team_id, road_team_id=road_team_id)
    ep.score_diff = score_diff
    return ep


def test_shot_event_home_team_shooting():
    ep = make_event_parser(score_diff=1)

    event = SimpleNamespace(
        type='SHOT', event_id=42,
        home_on_ice=[1, 2, 3], home_goalie=3,
        road_on_ice=[4, 5, 9], road_goalie=9,
        num_situation='EV')
    specific_event = SimpleNamespace(team_id=111, player_id=1)

    with patch('parsers.event_parser.ShotAttempt.find_by_event_id', return_value=None) as find_mock, \
            patch('parsers.event_parser.create_or_update_db_item') as create_mock:
        ep.get_shot_attempt_event(event, specific_event)

    find_mock.assert_called_once_with(42)
    assert create_mock.call_count == 1
    _, new_shot_attempt = create_mock.call_args[0]

    assert new_shot_attempt.game_id == 999
    assert new_shot_attempt.event_id == 42
    assert new_shot_attempt.shot_attempt_type == 'S'
    assert new_shot_attempt.num_situation == 'EV'
    assert new_shot_attempt.score_diff == 1
    assert new_shot_attempt.for_team_id == 111
    assert new_shot_attempt.against_team_id == 222
    assert new_shot_attempt.plr_situation == '2v2'
    assert new_shot_attempt.shooter_id == 1
    assert new_shot_attempt.for_player_ids == [1, 2, 3]
    assert new_shot_attempt.against_player_ids == [4, 5, 9]


def test_goal_event_is_stored_as_shot_type():
    ep = make_event_parser()

    event = SimpleNamespace(
        type='GOAL', event_id=43,
        home_on_ice=[1], home_goalie=None,
        road_on_ice=[4], road_goalie=None,
        num_situation='EV')
    specific_event = SimpleNamespace(team_id=111, player_id=1)

    with patch('parsers.event_parser.ShotAttempt.find_by_event_id', return_value=None), \
            patch('parsers.event_parser.create_or_update_db_item') as create_mock:
        ep.get_shot_attempt_event(event, specific_event)

    _, new_shot_attempt = create_mock.call_args[0]
    assert new_shot_attempt.shot_attempt_type == 'S'


def test_block_event_credits_shooting_team_as_for():
    # a block is still a shot attempt "for" the shooting team (Corsi
    # convention: blocked shots count as attempts for the shooter's team,
    # against for the blocking team). Shooting team 111 (players 1,2,3,
    # shooter is player 1) gets blocked by team 222 (players 4,5), which
    # registered the BLOCK event.
    ep = make_event_parser(score_diff=2)

    event = SimpleNamespace(
        type='BLOCK', event_id=100,
        home_on_ice=[1, 2, 3], home_goalie=None,
        road_on_ice=[4, 5], road_goalie=None,
        num_situation='PP')
    # the blocking player (team 222, road) is the one who registered the event
    specific_event = SimpleNamespace(
        team_id=222, player_id=4, blocked_player_id=1)

    with patch('parsers.event_parser.ShotAttempt.find_by_event_id', return_value=None), \
            patch('parsers.event_parser.create_or_update_db_item') as create_mock:
        ep.get_shot_attempt_event(event, specific_event)

    _, new_shot_attempt = create_mock.call_args[0]

    assert new_shot_attempt.shot_attempt_type == 'B'
    assert new_shot_attempt.for_team_id == 111
    assert new_shot_attempt.against_team_id == 222
    assert new_shot_attempt.shooter_id == 1
    assert new_shot_attempt.for_player_ids == [1, 2, 3]
    assert new_shot_attempt.against_player_ids == [4, 5]
    assert new_shot_attempt.plr_situation == '3v2'
    assert new_shot_attempt.score_diff == -2
    assert new_shot_attempt.num_situation == 'SH'


def test_missing_on_ice_data_is_skipped():
    ep = make_event_parser()

    event = SimpleNamespace(
        type='SHOT', event_id=44, home_on_ice=[], home_goalie=None,
        road_on_ice=[1], road_goalie=None, num_situation='EV')
    specific_event = SimpleNamespace(team_id=111, player_id=1)

    with patch('parsers.event_parser.create_or_update_db_item') as create_mock:
        ep.get_shot_attempt_event(event, specific_event)

    create_mock.assert_not_called()
