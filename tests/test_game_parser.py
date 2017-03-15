#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import requests
from lxml import html

from parsers.game_parser import GameParser


def test_2013_centre_bell():

    url = "http://www.nhl.com/scores/htmlreports/20132014/ES020001.HTM"

    game_id = str(os.path.splitext(os.path.basename(url))[0][2:])

    gp = GameParser(game_id, get_data(url))
    gp.load_data()
    attendance, venue = gp.retrieve_game_attendance_venue()
    assert attendance == 21273
    assert venue == "Centre Bell"


def get_data(url):
    r = requests.get(url)
    return html.fromstring(r.text)
