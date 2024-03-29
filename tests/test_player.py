#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.player import Player


def test_constructor():
    plr = Player(8467353, "Antropov", "Nik", "C", alternate_first_names=['Nikolai'])
    assert plr.player_id == 8467353
    assert plr.first_name == "Nik"
    assert plr.last_name == "Antropov"
    assert plr.name == "Nik Antropov"
    assert plr.position == "C"
    assert plr.alternate_first_names == ['Nikolai']
    assert hasattr(plr, "alternate_last_names") is True
    assert plr.alternate_last_names is None


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


def test_find_by_name_extended_caps():
    plr = Player.find_by_name_extended("ANDREI", "VASILEVSKIY")
    assert plr.player_id == 8476883


def test_find_by_name_extended_caps_not_working_yet():
    plr = Player.find_by_name_extended("TJ", "GALIARDI")
    assert plr.player_id == 8474001


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
