#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dateutil.parser import parse

from db.player_data_item import PlayerDataItem
from db.player import Player
from utils.player_data_retriever import PlayerDataRetriever
from utils import feet_to_m, lbs_to_kg


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


# def test_player_data_retriever():

#     pdi = PlayerDataRetriever()
#     raw_player_data = pdi.retrieve_raw_player_data(8447687)

#     assert raw_player_data['first_name'] == 'Dominik'
#     assert raw_player_data['last_name'] == 'Hasek'
#     assert raw_player_data['full_name'] == 'Dominik Hasek'
#     assert raw_player_data['position'] == 'G'
#     assert raw_player_data['number'] == '39'
#     assert raw_player_data["height_metric"] == feet_to_m(6, 1)
#     assert raw_player_data["height_imperial"] == 6.01
#     assert raw_player_data["weight_metric"] == round(lbs_to_kg(166))
#     assert raw_player_data["weight_imperial"] == 166
#     assert raw_player_data["hand"] == 'L'
#     assert raw_player_data["date_of_birth"] == parse('1965-01-29').date()
#     assert raw_player_data["place_of_birth"] == 'Pardubice, CZE'
