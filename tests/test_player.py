#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.player import Player


def test_find_by_id():
    plr = Player.find_by_id(8459469)
    assert plr.name == "Rory Fitzpatrick"


def test_name_property():
    plr = Player.find_by_id(8459457)
    assert plr.name == " ".join((plr.first_name, plr.last_name))


def test_comparison_operators():
    plr_1 = Player.find_by_id(8450900)
    plr_2 = Player.find_by_id(8450900)
    plr_3 = Player.find_by_id(8449895)
    assert plr_1 == plr_2
    assert plr_2 != plr_3


def test_str_function():
    plr_1 = Player.find_by_id(8477939)
    assert str(plr_1) == "[8477939] William Nylander"
