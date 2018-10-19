#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from dateutil.parser import parse

from db.team import Team
from db.player import Player
from utils.player_finder import PlayerFinder


ACTIONS = [
    'signed', 're-signed', 'acquired',
    'announced', 'agreed', 'claimed',
    'bought', 'released', 'terminated'
    ]

OTHER_ACTIONS = [
    'named', 'offered', 'promoted',
    'fired', 'extended', 'renewed',
    'received', 'waived', 're-assigned',
    'tendered', 'voided', 'issued',
    'filed', 'declined', 'relieved',
    'assigned', 'added', 'placed',
    'exercised', 'invited', 'reached',
    'elected', 'suspended', 'granted',
    'lifted', 'made', 'purchased',
    'completed', 'demoted', 'picked',
    'retained'
]

POSITIONS = ['center', 'defenseman', 'goaltender', 'left wing', 'right wing']
POSITION_PLURALS = [
    'centers', 'defensemen', 'goaltenders', 'left wings', 'right wings']

SEMICOLON_REGEX = re.compile(";\s+(?!previously|later|\d+)")
# regular expression for waiver claims
CLAIM_FROM_REGEX = re.compile(
    "(?:C|c)laimed (%s) (.+) (?:off|on) " % "|".join(POSITIONS) +
    "(?:re-entry )?waivers from the (.+)\.?$")
# regular expression for signings w/ contract lengths
SIGNING_WITH_CONTRACT_REGEX = re.compile(
    "(?:S|s)igned (%s)" % "|".join(POSITIONS) +
    "(?:\/)?(?:%s)?" % "|".join(POSITIONS) +
    " ([A-za-z\.\-\s']+)" +
    "(?:(?:, who had been with .+)|(?:, their .+))? to an? " +
    "(?:(.+)\-year )contract(?: \(.+\))?\.?$")
# regular expression for signings w/o contract lengths
SIGNING_REGEX = re.compile(
    "(?:S|s)igned (%s) ([A-za-z\.\-\s']+)" % "|".join(POSITIONS) +
    "(?:(?:, who had been with .+)|(?:, their .+))?\.?$")
# regular expression for multiple signings w/ contract lengths
MULTIPLE_SIGNING_WITH_CONTRACT_REGEX = re.compile(
    "(?:S|s)igned (.+) to (?:(.+)\-year )contracts\.?$")
# regular expression for multiple signings w/o contract lengths
MULTIPLE_SIGNING = re.compile(
    "(?:S|s)igned (.+).?$")


def retrieve_waiver_claim_information(raw_data):
    """
    Retrieves transaction information for a waiver claim, e.g. *Claimed ...
    off waivers from the ...*
    """
    if raw_data.endswith("."):
        raw_data = raw_data[:-1]
    match = re.search(CLAIM_FROM_REGEX, raw_data)
    try:
        pos, plr_name, team_name = match.group(1, 2, 3)
    except Exception as e:
        print("+ Unable to retrieve feasible information from '%s'", raw_data)

    return pos, plr_name, team_name


def retrieve_waiver_claim(transaction_raw_data):
    """
    Retrieves transaction properties for a waiver claim.
    """
    (position, plr_name, other_team_name) = (
        retrieve_waiver_claim_information(transaction_raw_data))
    # finding second team in transaction
    other_team = Team.find_by_name(other_team_name)
    if other_team is None:
        print(
            "+ Unable to find second team in " +
            "transaction in '%s'" % transaction_raw_data)
        return

    # using only first letter of found position
    position = position[0]
    # first trying to find player by full name and position
    plr = Player.find_by_full_name(plr_name, position[0])
    # then trying to find player by full name only
    if plr is None:
        plr = Player.find_by_full_name(plr_name)
    # at last naively splitting full name into first and last name and
    # trying to find player accordingly
    if plr is None:
        first_name, last_name = plr_name.split(" ", 2)
        plr = Player.find_by_name_extended(
            first_name, last_name)

    if plr is None:
        print(
            "+ Unable to find transferred player " +
            "in '%s'" % transaction_raw_data)
        return

    return plr, other_team


def find_player_in_transaction(position, plr_name):
    """
    Finds actual player in database.
    """
    # first trying to find player by full name and position
    plr = Player.find_by_full_name(plr_name, position[0])
    # then trying to find player by full name only
    if plr is None:
        plr = Player.find_by_full_name(plr_name)
    # at last naively splitting full name into first and last name and
    # trying to find player accordingly
    if plr is None:
        first_name, last_name = plr_name.strip().split(" ", 2)[:2]
        plr = Player.find_by_name_extended(
            first_name, last_name)
    return plr


def retrieve_signing(transaction_raw_data):

    signings = retrieve_signing_information(transaction_raw_data)
    signed_players = list()

    for signing in signings:
        if len(signing) == 3:
            position, plr_name, length = signing
        else:
            position, plr_name = signing
        plr = find_player_in_transaction(position, plr_name)

        if plr is None:
            print(transaction_raw_data, plr_name)
            pfr = PlayerFinder()
            suggestions = pfr.get_suggested_players(plr_name)
            print(suggestions)
        else:
            signed_players.append(plr)

    return signed_players


def retrieve_signing_information(transaction_raw_data):
    """
    Retrieves transaction properties for a contract signing.
    """
    signings = list()
    # skipping contract extensions, offer sheets and tryouts
    if any(
        s in transaction_raw_data for s in [
            "extension", "offer sheet", "tryout"]):
        return signings

    # processing multiple signings w/ contract indication
    if "contracts" in transaction_raw_data:
        match = re.search(
            MULTIPLE_SIGNING_WITH_CONTRACT_REGEX, transaction_raw_data)
        if match:
            # retrieving contract length
            length = match.group(2)
            # exploding multiple signings to list of single signings
            tokens = [
                s.strip() for s in re.split(",\s?|and ", match.group(1)) if s]
            # handling each signing separately
            for token in tokens:
                match = re.search(
                    "(%s)\s(.+)" % "|".join(
                        POSITIONS + POSITION_PLURALS), token)
                if match:
                    # retrieving position (using only first letter) from match
                    position = match.group(1)[0].upper()
                    # retrieving player name from match
                    plr_name = match.group(2)
                    signings.append((position, plr_name, length))
                else:
                    # skipping 'who had been...' tokens
                    if token.startswith("who"):
                        continue
                    # retaining previous position, interpreting token as a name
                    signings.append((position, token, length))
        else:
            print(
                "+ Unable to retrieve feasible information about multiple " +
                "contract signings from '%s'" % transaction_raw_data)
    # processing single signings w/ contract indication
    elif "contract" in transaction:
        match = re.search(SIGNING_WITH_CONTRACT_REGEX, transaction_raw_data)
        if match:
            # retrieving position (using only first letter) from match
            position = match.group(1)[0].upper()
            plr_name = match.group(2)
            length = match.group(3)
            signings.append((position, plr_name, length))
        else:
            print(
                "+ Unable to retrieve single contract signing " +
                "from '%s'" % transaction_raw_data)
    # processing multiple signings w/o contract indication
    elif "and " in transaction:
        match = re.search(MULTIPLE_SIGNING, transaction_raw_data)
        if match:
            tokens = [
                re.sub(
                    "\.$", "", s).strip() for s in re.split(
                        ",\s?|and ", match.group(1)) if s]
            for token in tokens:
                match = re.search(
                    "(%s)\s(.+)" % "|".join(
                        POSITIONS + POSITION_PLURALS), token)
                if match:
                    position = match.group(1)[0].upper()
                    # getting rid of periods at the end of player names
                    plr_name = re.sub("\.$", "", match.group(2))
                    plr_name = match.group(2)
                    signings.append((position, plr_name))
                else:
                    if token.startswith("who"):
                        continue
                    signings.append((position, token))
    # processing single signings w/o contract indication at last
    else:
        match = re.search(SIGNING_REGEX, transaction_raw_data)
        if match:
            position = match.group(1)[0].upper()
            # getting rid of a possible period at the end of a player name
            plr_name = re.sub("\.$", "", match.group(2))
            signings.append((position, plr_name))
        else:
            print(
                "+ Unable to retrieve single signing " +
                "from '%s'" % transaction_raw_data)

    return signings


if __name__ == '__main__':

    import sys
    year = sys.argv[1]

    src = R"C:\docs\nhl_transactions\transactions_%s.txt" % year

    curr_date = ''

    with open(src) as file:
        lines = [l.strip() for l in file.readlines() if l.strip()]

    for line in lines[:]:
        # trying to parse line into a date
        try:
            curr_date = parse(line).date()
            continue
        except ValueError:
            pass
        # trying to retrieve both team name and transaction raw data
        try:
            team, data = [token.strip() for token in line.split(":")]
        except Exception as e:
            print(line)
        # retrieving team from team name
        team = Team.find_by_name(team)
        if team is None:
            print(line)

        # splitting full transaction raw data into separate transactions
        transactions = re.split(SEMICOLON_REGEX, data)
        for transaction in transactions:
            try:
                action = transaction.split()[0].lower()
                if action not in ACTIONS:
                    continue
                if action == 'claimed':
                    plr, other_team = retrieve_waiver_claim(transaction)
                    print(
                        "%s Claim: %s - %s -> %s" % (
                            curr_date, plr, other_team, team))
                elif action == 'signed':
                    plrs = retrieve_signing(transaction)
                    for plr in plrs:
                        print("%s Signing: %s -> %s" % (curr_date, plr, team))

            except IndexError:
                print(line)
