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
from db.contract import Contract
from db.player_data_item import PlayerDataItem
from utils import remove_non_ascii_chars

logger = logging.getLogger(__name__)

CAPFRIENDLY_PLAYER_PREFIX = "http://www.capfriendly.com/players/"
CAPFRIENDLY_TEAM_PREFIX = "http://www.capfriendly.com/teams/"

LATEST_SIGNINGS_TEMPLATE = (
    "http://www.capfriendly.com/ajax/new_additions_load_more?p=%d")


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
        capfriendly_id = tr.xpath("td/a/@href").pop(0).split("/")[-1]

        # trying to find player by capfriendly id first
        plr = Player.find_by_capfriendly_id(capfriendly_id)
        if plr:
            continue

        last_name, first_name = player_name.split(", ")
        plr = Player.find_by_name_extended(first_name, last_name)
        # new capfriendly id
        if plr and plr.capfriendly_id is None:
            print(
                "+ Found capfriendly id for %s: %s" % (plr, capfriendly_id))
            add_capfriendly_id_to_player(plr, capfriendly_id)
        # updated capfriendly id
        if plr and plr.capfriendly_id != capfriendly_id:
            print(
                "+ Found updated capfriendly id for %s: %s (was %s)" % (
                    plr, capfriendly_id, plr.capfriendly_id))
            add_capfriendly_id_to_player(plr, capfriendly_id)
        # no unique player found
        if plr is None:
            print(
                "+ No (unique) player for capfriendly id: %s (%s %s)" % (
                    capfriendly_id, first_name, last_name))


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
        # creating actual capfriendly id used in url query
        query_id = potential_capfriendly_id.replace(" ", "-")
        url = "".join((CAPFRIENDLY_PLAYER_PREFIX, query_id))
        req = requests.get(url)
        doc = html.fromstring(req.text)
        # retrieving page title (i.e. player name) from capfriendly page
        page_header = doc.xpath("//h1/text()").pop(0).strip().replace(".", "")
        # removing non-ascii characters from page title
        page_header = remove_non_ascii_chars(page_header)
        if page_header == 'Player not found':
            continue
        # retrieving player's date of birth from capfriendly page
        page_dob = doc.xpath(
            "//span[@class='l pld_l']/ancestor::div/text()")[0].strip()
        page_dob = parse(page_dob).date()

        # testing actual name (i.e. potential capfriendly id converted to
        # upper case and stripped of *.* characters) contains page header
        # (converted to upper)
        if page_header.upper() in potential_capfriendly_id.upper().replace(
                ".", ""):
            # comparing date of births
            if page_dob == pdi.date_of_birth:
                capfriendly_id_found = True
                # removing dots from id used in query to create
                # actual capfriendly id
                found_capfriendly_id = query_id.replace(
                    ".", "").replace("'", "")
                logger.info(
                    "+ Found capfriendly id for %s: %s" % (
                        plr.name, found_capfriendly_id))
                add_capfriendly_id_to_player(plr, found_capfriendly_id)

    if not capfriendly_id_found:
        logger.warn("+ No capfriendly id found for %s" % plr.name)

    return plr.capfriendly_id


def collect_potential_capfriendly_ids(plr):
    """
    Compiles all potential combinations of player first and last names
    to find a potential capfriendly id. Removes non-ascii characters from
    resulting strings to allow for usage in urls.
    """
    # listing all of players' potential first names
    first_names = [plr.first_name]
    if plr.alternate_first_names:
        first_names += plr.alternate_first_names
    # removing non-ascii characters from all collected first names
    first_names = [remove_non_ascii_chars(s) for s in first_names]
    first_names = set(map(str.lower, first_names))

    # listing all of players' potential last names
    last_names = [plr.last_name]
    # extending list of last names to include an item equalling last name with
    # a following '1' (usually done by capfriendly, too)
    last_names.extend(["".join((plr.last_name, '1'))])
    if plr.alternate_last_names:
        last_names += plr.alternate_last_names
    # removing non-ascii characters from all collected last names
    last_names = [remove_non_ascii_chars(s) for s in last_names]
    last_names = set(map(str.lower, last_names))

    # returning all potential combinations of players' first and last names
    return list(map(" ".join, itertools.product(first_names, last_names)))


def add_capfriendly_id_to_player(plr, capfriendly_id):
    """
    Adds specified capfriendly id to given player item.
    """
    plr.capfriendly_id = capfriendly_id
    with session_scope() as session:
        session.merge(plr)
        session.commit()


def retrieve_latest_signings(stop_threshold=5):
    """
    Retrieves latest player signings traversing the corresponding section on
    capfriendly.com. Creates contract data items for each signing. Stops when
    a given threshold of contracts is reached that already existedd
    in the database.
    """

    url = LATEST_SIGNINGS_TEMPLATE % 1
    r = requests.get(url)
    doc = html.fromstring(r.json()['html'])

    raw_signed_players = doc.xpath("tr/td/a[contains(@href, 'players')]/@href")

    from utils.player_contract_retriever import PlayerContractRetriever
    pcr = PlayerContractRetriever()

    for raw_signed_player in raw_signed_players[:4]:
        capfriendly_id = raw_signed_player.split("/")[-1]
        print(capfriendly_id)

        plr = Player.find_by_capfriendly_id(capfriendly_id)

        raw_contract_data = pcr.retrieve_raw_contract_data_by_capfriendly_id(
            capfriendly_id)

        most_recent_contract_raw_data = raw_contract_data[0]

        contract = Contract(plr.player_id, most_recent_contract_raw_data)
        contract_db = Contract.find_with_team(
            plr.player_id,
            most_recent_contract_raw_data['start_season'],
            most_recent_contract_raw_data['end_season'],
            most_recent_contract_raw_data['signing_team_id'])

        if contract_db is None:
            print("Contract not in database yet")
        elif contract_db != contract:
            print("Database contract needs to be updated")
        elif contract_db == contract:
            print("Contract already in database")
