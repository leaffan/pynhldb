#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils.eliteprospects_utils import get_player_with_dob


def test_get_player_with_dob():
    # Auston Matthews
    url = "http://www.eliteprospects.com/player.php?player=199898"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Auston"
    assert plr.last_name == "Matthews"
    assert plr.date_of_birth == "1997-09-17"


def test_get_player_with_alternate_first_and_last_name():
    # Nikolai Kulyomin a.k.a. "Nikolay Kulemin"
    url = "http://www.eliteprospects.com/player.php?player=9258"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Nikolai"
    assert plr.last_name == "Kulyomin"
    assert plr.date_of_birth == "1986-07-14"
    assert plr.alt_last_name == "Kulemin"


def test_get_player_with_multiple_alternate_last_names():
    # Igor Shvyryov a.k.a. "Igor Shvyrev, Svyrev, Shvyrov"
    url = "http://www.eliteprospects.com/player.php?player=312234"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Igor"
    assert plr.last_name == "Shvyryov"
    assert plr.date_of_birth == "1998-07-10"
    assert plr.alt_last_name == "Shvyrev"


def test_get_player_without_alternate_last_name():
    # T.J. Oshie a.k.a. "Timothy, TJ Oshie"
    url = "http://www.eliteprospects.com/player.php?player=9209"
    plr = get_player_with_dob(url)
    assert plr.first_name == "T.J."
    assert plr.last_name == "Oshie"
    assert plr.date_of_birth == "1986-12-23"
    assert plr.alt_last_name == ""

    # Freddy Meyer a.k.a. "Frederick Meyer IV" (not grasped by function yet)
    url = "http://www.eliteprospects.com/player.php?player=8837"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Freddy"
    assert plr.last_name == "Meyer"
    assert plr.date_of_birth == "1981-01-04"
    assert plr.alt_last_name == ""

    # Nicklaus Perbix aka. "Nicholas, Nick Perbix"
    url = "http://www.eliteprospects.com/player.php?player=380612"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Nicklaus"
    assert plr.last_name == "Perbix"
    assert plr.date_of_birth == "1998-06-15"
    assert plr.alt_last_name == ""


def test_get_player_with_alternate_last_name():
    # Nikita A. Popugayev a.k.a. "Nikita A. Popugaev"
    url = "http://www.eliteprospects.com/player.php?player=312680"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Nikita A."
    assert plr.last_name == "Popugayev"
    assert plr.date_of_birth == "1998-11-20"
    assert plr.alt_last_name == "Popugaev"

    # Zane McIntyre a.k.a. "Zane Gothberg"
    url = "http://www.eliteprospects.com/player.php?player=75336"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Zane"
    assert plr.last_name == "McIntyre"
    assert plr.date_of_birth == "1992-08-20"
    assert plr.alt_last_name == "Gothberg"

    # Jonathan Marchessault a.k.a. "Jonathan Audy-Marchessault"
    url = "http://www.eliteprospects.com/player.php?player=32872"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Jonathan"
    assert plr.last_name == "Marchessault"
    assert plr.date_of_birth == "1990-12-27"
    assert plr.alt_last_name == "Audy-Marchessault"


def test_get_player_wrongly_encoded_last_name():
    # Dominik Lakatos a.k.a. "Dominik Lakatoš"
    url = "http://www.eliteprospects.com/player.php?player=195562"
    plr = get_player_with_dob(url)
    assert plr.first_name == "Dominik"
    assert plr.last_name == "Lakatos"
    assert plr.date_of_birth == "1997-04-08"
    assert plr.alt_last_name == "Lakato\x9a"
