#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.player import Player


def test_constructor():
    plr = Player(99, "Gretzky", "Wayne", "C", alternate_last_names=['Bruce'])
    assert plr.player_id == 99
    assert plr.first_name == "Wayne"
    assert plr.last_name == "Gretzky"
    assert plr.name == "Wayne Gretzky"
    assert plr.position == "C"
    assert plr.alternate_last_names == ['Bruce']
    assert hasattr(plr, "alternate_first_names") is True
    assert plr.alternate_first_names is None


def test_find_by_id():
    plr = Player.find_by_id(8459469)
    assert plr.name == "Rory Fitzpatrick"


def test_find_by_name():
    plr = Player.find_by_name("Jaromir", "Jagr")
    assert plr.player_id == 8448208


def test_find_by_name_position():
    plr = Player.find_by_name_position("Sidney", "Crosby", "C")
    assert plr.player_id == 8471675


def test_find_by_name_extended():
    plr = Player.find_by_name_extended("Mitch", "Marner")
    assert plr.player_id == 8478483


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
