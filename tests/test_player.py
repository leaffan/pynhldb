#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.player import Player


def test_find_by_id():
    plr = Player.find_by_id(8459469)
    assert plr.name == "Rory Fitzpatrick"


def test_name_property():
    plr = Player.find_by_id(8459457)
    assert plr.name == " ".join((plr.first_name, plr.last_name))

