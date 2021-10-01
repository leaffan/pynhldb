#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.player_season import PlayerSeason
from db.goalie_season import GoalieSeason
from db.team import Team


def test_player_season_comparison():
    team = Team.find_by_id(10)
    plr_season_1 = PlayerSeason.find(8451774, team, 1994, 'RS', 1)
    plr_season_2 = PlayerSeason.find(8451774, team, 1994, 'PO', 1)
    assert plr_season_1 == plr_season_1
    assert plr_season_1 < plr_season_2
    assert not plr_season_1 > plr_season_2


def test_find_all_player_seasons():
    """
    Tests correct number of player season items (regular and playoff) for
    selected goaltender.
    """
    plr_seasons = PlayerSeason.find_all(8446053)
    assert len(plr_seasons) == 51


def test_goalie_season_comparison():
    team = Team.find_by_id(7)
    goalie_season_1 = GoalieSeason.find(8447687, team, 1994, 'PO', 1)
    goalie_season_2 = GoalieSeason.find(8447687, team, 1993, 'RS', 1)
    assert goalie_season_1 == goalie_season_1
    assert goalie_season_2 < goalie_season_1
    assert not goalie_season_2 > goalie_season_1


def test_find_all_goalie_seasons():
    """
    Tests correct number of goalie season items (regular and playoff) for
    selected goaltender.
    """
    goalie_seasons = GoalieSeason.find_all(8448382)
    assert len(goalie_seasons) == 33
