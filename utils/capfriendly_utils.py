#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import itertools

import requests
from lxml import html
from dateutil.parser import parse

from db.common import session_scope
from db.team import Team
from db.player import Player
from db.player_data_item import PlayerDataItem

logger = logging.getLogger(__name__)

CAPFRIENDLY_PLAYER_PREFIX = "http://www.capfriendly.com/players/"
CAPFRIENDLY_TEAM_PREFIX = "http://www.capfriendly.com/teams/"


def retrieve_capfriendly_ids(team_id):
    """
    Retrieves ids from capfriendly.com for all players of the team with
    the specified id
    """
    team = Team.find_by_id(team_id)

    logger.info(
        "+ Retrieving capfriendly ids for all players of the %s" % team)

    url = "".join((
        CAPFRIENDLY_TEAM_PREFIX,
        team.team_name.replace(" ", "").lower()))

    r = requests.get(url)
    doc = html.fromstring(r.text)

    player_name_trs = doc.xpath("//tr[@class='even c' or @class='odd c']")

    for tr in player_name_trs:
        player_name = tr.xpath("td/a/text()").pop(0)
        player_link = tr.xpath("td/a/@href").pop(0)
        player_position = tr.xpath("td[3]/span/text()")
        if player_position:
            player_position = player_position.pop(0)
        else:
            player_position = ''

        last_name, first_name = player_name.split(", ")
        plr = Player.find_by_name_extended(first_name, last_name)
        if plr is None and player_position:
            primary_position = player_position.split(", ")[0][0]
            plr = Player.find_by_name_position(
                first_name, last_name, primary_position)
        if plr and plr.capfriendly_id is None:
            print(
                "+ Ambigious capfriendly id for player:", first_name,
                last_name, plr, player_link.split("/")[-1])
        if plr is None:
            print(
                "+ No player for capfriendly id:", first_name,
                last_name, player_link.split("/")[-1])


def retrieve_capfriendly_id(player_id):
    """
    Retrieves an id from capfriendly.com for the player with the
    specified id.
    """
    plr = Player.find_by_id(player_id)
    pdi = PlayerDataItem.find_by_player_id(player_id)

    if plr.capfriendly_id is not None:
        logger.info(
            "+ Existing capfriendly id for %s: %s" % (
                plr.name, plr.capfriendly_id))
        return plr.capfriendly_id

    # compiling all potential capfriendly ids from the player's name(s)
    potential_capfriendly_ids = collect_potential_capfriendly_ids(plr)

    capfriendly_id_found = False

    while potential_capfriendly_ids and not capfriendly_id_found:
        potential_capfriendly_id = potential_capfriendly_ids.pop(0)
        query_id = potential_capfriendly_id.replace(" ", "-")
        url = "".join((CAPFRIENDLY_PLAYER_PREFIX, query_id))
        req = requests.get(url)
        doc = html.fromstring(req.text)
        # retrieving player name from capfriendly page
        page_header = doc.xpath("//h1/text()").pop(0).strip()
        # retrieving player's date of birth from capfriendly page
        page_dob = doc.xpath(
            "//span[@class='l pld_l']/ancestor::div/text()")[0].strip()
        page_dob = parse(page_dob).date()
        # comparing names
        if page_header == potential_capfriendly_id.upper():
            # comparing date of births
            if page_dob == pdi.date_of_birth:
                capfriendly_id_found = True
                logger.info(
                    "+ Found capfriendly id for %s: %s" % (plr.name, query_id))
                plr.capfriendly_id = query_id
                with session_scope() as session:
                    session.merge(plr)
                    session.commit()

    if not capfriendly_id_found:
        logger.warn("+ No capfriendly id found for %s" % plr.name)

    return plr.capfriendly_id


def collect_potential_capfriendly_ids(plr):
    """
    Compiles all potential combinations of player first and last names
    to find a potential capfriendly id.
    """
    # listing all of players' potential first names
    first_names = [plr.first_name]
    if plr.alternate_first_names:
        first_names += plr.alternate_first_names
    first_names = list(map(str.lower, first_names))

    # listing all of players' potential last names
    last_names = [plr.last_name]
    if plr.alternate_last_names:
        last_names += plr.alternate_last_names
    last_names = list(map(str.lower, last_names))

    return list(map(" ".join, itertools.product(first_names, last_names)))
