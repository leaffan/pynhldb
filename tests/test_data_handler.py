#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from utils.data_handler import DataHandler


src_rs = R"D:\nhl\official_and_json\2015-16\2016-04\2016-04-10.zip"
src_po = R"D:\nhl\official_and_json\2015-16\2016-04\2016-04-13.zip"


def test_find_html_data():
    dh_rs = DataHandler(src_rs)
    dh_po = DataHandler(src_po)

    html_files_rs = dh_rs._get_contents()
    html_files_po = dh_po._get_contents()

    assert len(html_files_rs) == 16
    assert len(html_files_po) == 24


def test_find_json_data():
    dh_rs = DataHandler(src_rs)
    dh_po = DataHandler(src_po)

    json_files_rs = dh_rs._get_contents('json')
    json_files_po = dh_po._get_contents('.JSON')

    assert len(json_files_rs) == 4
    assert len(json_files_po) == 6


def test_get_html_data():
    dh_rs = DataHandler(src_rs)
    dh_po = DataHandler(src_po)

    html_data_rs = dh_rs.get_game_data(dh_rs.game_ids[0])
    html_data = open(html_data_rs['ES']).read()
    assert "Event Summary" in html_data
    assert "Game %s" % dh_rs.game_ids[0][2:] in html_data
    dh_rs.clear_temp_files()

    html_data_po = dh_po.get_game_data(dh_po.game_ids[-1], 'GS')
    html_data = open(html_data_po['GS']).read()
    assert "Game Summary" in html_data
    assert "Game %s" % dh_po.game_ids[-1][2:] in html_data
    dh_po.clear_temp_files()


def test_get_json_data():
    dh_rs = DataHandler(src_rs)
    dh_po = DataHandler(src_po)

    json_data_rs = dh_rs.get_game_json_data(dh_rs.game_ids[-1])
    json_data = json.loads(open(json_data_rs).read())
    assert str(json_data['gameData']['game']['pk'])[4:] == dh_rs.game_ids[-1]
    dh_rs.clear_temp_files()

    json_data_po = dh_po.get_game_json_data(dh_po.game_ids[0])
    json_data = json.loads(open(json_data_po).read())
    assert str(json_data['gameData']['game']['pk'])[4:] == dh_po.game_ids[0]
    dh_po.clear_temp_files()
