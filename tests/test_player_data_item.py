#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.player_data_item import PlayerDataItem
from db.player import Player


def test_find_by_id():
    pdi = PlayerDataItem.find_by_player_id(8477939)
    plr = Player.find_by_id(pdi.player_id)
    assert plr.name == 'William Nylander'
    assert pdi.location == 'Calgary, AB, CAN'


def test_find_by_ids():
    pdis = PlayerDataItem.find_by_player_ids([8462042, 8470595])
    plr_1 = Player.find_by_id(pdis[0].player_id)
    plr_2 = Player.find_by_id(pdis[1].player_id)
    assert plr_1.name == "Jarome Iginla"
    assert plr_2.name == "Eric Staal"


def test_comparison_operators():
    pdi_1 = PlayerDataItem.find_by_player_id(8449645)
    pdi_2 = PlayerDataItem.find_by_player_id(8449645)
    pdi_3 = PlayerDataItem.find_by_player_id(8446053)
    assert pdi_1 == pdi_2
    assert pdi_1 != pdi_3
