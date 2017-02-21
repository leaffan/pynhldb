#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.player_draft import PlayerDraft
from db.team import Team


def test_find_by_id():
    pdft = PlayerDraft.find_by_player_id(8475883)  # Frederik Andersen
    assert len(pdft) == 2
    pdft = PlayerDraft.find_by_player_id(8466145)  # Nick Boynton
    assert len(pdft) == 2


def test_find():
    pdft = PlayerDraft.find(8479318, 10, 2016)  # Auston Matthews
    assert pdft.round == 1
    assert pdft.overall == 1


def test_constructor():
    pdft = PlayerDraft(8999444, 1, 2018, 3, 75)  # fictional player
    assert pdft.player_id == 8999444
    assert Team.find_by_id(pdft.team_id).name == 'New Jersey Devils'
    assert pdft.year == 2018
    assert pdft.round == 3
    assert pdft.overall == 75


def test_comparison_operators():
    pdft_kopitar = PlayerDraft.find_by_player_id(8471685).pop(0)  # 2005, 11
    pdft_toews = PlayerDraft.find_by_player_id(8473604).pop(0)  # 2006, 3
    pdft_kessel = PlayerDraft.find_by_player_id(8473548).pop(0)  # 2006, 5
    pdft_stamkos = PlayerDraft.find_by_player_id(8474564).pop(0)  # 2008, 1
    ordered = sorted([pdft_kessel, pdft_kopitar, pdft_stamkos, pdft_toews])
    assert ordered[0] == pdft_kopitar
    assert ordered[1] == pdft_toews
    assert ordered[2] == pdft_kessel
    assert ordered[3] == pdft_stamkos
