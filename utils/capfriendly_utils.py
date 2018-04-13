#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import itertools

import requests
from lxml import html
from dateutil.parser import parse

from db import commit_db_item
from db.common import session_scope
from db.team import Team
from db.player import Player
from db.contract import Contract
from db.contract_year import ContractYear
from db.player_data_item import PlayerDataItem
from utils import remove_non_ascii_chars
from utils.player_contract_retriever import PlayerContractRetriever
from utils.player_finder import PlayerFinder

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


def retrieve_latest_signings(max_existing_contracts_found=5):
    """
    Retrieves latest player signings traversing the corresponding section on
    capfriendly.com. Creates contract data items for each signing. Stops when
    a given threshold of contracts is reached that already existedd
    in the database.
    """
    existing_contracts_found = 0

    i = 1

    # TODO: reduce complexity and length of this function
    while existing_contracts_found < max_existing_contracts_found:
        url = LATEST_SIGNINGS_TEMPLATE % i
        r = requests.get(url)
        doc = html.fromstring(r.json()['html'])

        # retrieving links to pages of recently signed players
        recently_signed_player_links = doc.xpath(
            "tr/td/a[contains(@href, 'players')]/@href")
        # retrieving names of recently signed players
        recently_signed_player_names = doc.xpath("tr/td/a/text()")
        # retrieving positions of recently signed players
        recently_signed_player_positions = doc.xpath("tr/td[3]/text()")
        # retrieving signing dates of recently signed players
        recent_signing_dates = [
            parse(x).date() for x in doc.xpath("tr/td[5]/text()")]
        recent_signings = zip(
            recently_signed_player_names,
            recently_signed_player_links,
            recent_signing_dates,
            recently_signed_player_positions
        )

        pcr = PlayerContractRetriever()

        for signee, link, signing_date, positions in recent_signings:
            # retrieving capfriendly id and subsequentially corresponding
            # player
            capfriendly_id = link.split("/")[-1]
            plr = Player.find_by_capfriendly_id(capfriendly_id)

            if plr is None:
                # multiple positions are possible, i.e. "RW, C"
                # stripping and using only first letter of position, i.e. "R"
                # instead of "RW"
                positions = [p.strip()[0] for p in positions.split(",")]
                for pos in positions:
                    plr = Player.find_by_full_name(signee, pos)
                    if plr:
                        break

            # TODO: try to find player by name in case no valid capfriendly
            # id exists
            if plr is None:
                print(
                    "+ Contracted player (%s) not found in database" % signee)
                pfr = PlayerFinder()
                first_name, last_name = signee.split()
                suggested_players = pfr.get_suggested_players(
                    last_name, first_name)
                if len(suggested_players) == 1:
                    (
                        nhl_id, pos, sugg_last_name, sugg_first_name, dob
                    ) = suggested_players.pop()
                    if (
                        first_name, last_name
                    ) == (
                        sugg_first_name, sugg_last_name
                    ):
                        pfr.create_player(
                            nhl_id, sugg_last_name, sugg_first_name,
                            pos, capfriendly_id=capfriendly_id)
                        plr = Player.find_by_capfriendly_id(capfriendly_id)
                        print("+ Player %s created in database" % plr)
                    # TODO: error handling, date of birth checking
                    else:
                        continue
                else:
                    continue

            # trying to find existing contract(s) signed on this date
            # in database
            contracts_db = Contract.find_with_signing_date(
                plr.player_id, signing_date)

            if contracts_db:
                if len(contracts_db) > 1:
                    print(
                        "+++ Multiple contracts found for %s " % plr.name +
                        "(%d) on signing date %s" % (
                            plr.player_id, signing_date))
                print("+ Contract for %s signed on %s already in database" % (
                    plr.name, signing_date))
                existing_contracts_found += 1
            else:
                print(
                    "+ Contract for %s signed on " % plr.name +
                    "%s not found in database yet" % signing_date)
                # retrieving all contracts associated with current
                # capfriendly id
                raw_contract_list = (
                    pcr.retrieve_raw_contract_data_by_capfriendly_id(
                        capfriendly_id))

                # finding contract signed on signing date in list of all
                # contracts and creating it along with corresponding contract
                # years
                for raw_contract in raw_contract_list:
                    if raw_contract['signing_date'] == signing_date:
                        contract = Contract(plr.player_id, raw_contract)
                        commit_db_item(contract)
                        for raw_contract_year in raw_contract[
                                'contract_years']:
                                    contract_year = ContractYear(
                                        plr.player_id,
                                        contract.contract_id,
                                        raw_contract_year)
                                    commit_db_item(contract_year)
                        break

            if existing_contracts_found >= max_existing_contracts_found:
                break

        i += 1
