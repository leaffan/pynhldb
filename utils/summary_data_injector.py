#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging

import requests
from lxml import html

from db.player import Player

logger = logging.getLogger(__name__)

JSON_SUMMARY_URL_TEMPLATE = (
    "http://statsapi.web.nhl.com/api/v1/game/%s/feed/live")


def add_nhl_ids_to_content(url, content):
    """
    Adds player ids used by nhl.com to each roster player on event summary
    to allow for a unique identification later on.
    """

    season = int(os.path.dirname(url).split("/")[-1][:4])
    game_id = os.path.basename(url).split(".")[0][2:]

    # setting up fully qualified game id to be used in boxscore url
    full_game_id = "%d%s" % (season, game_id)
    # retrieving json summary from  NHL stats API
    summary = retrieve_summary(full_game_id)

    # if json boxscore is valid, use it to retrieve nhl player ids from it
    if summary and 'liveData' in summary.keys():
        road_players, home_players = retrieve_player_ids_from_summary(summary)
    # sometimes json summaries are missing
    # alternative is to retrieve nhl player ids from the database itself
    # prerequisite: players have to be in database already and must be
    # uniquely identifiable by name, prename and position
    else:
        logger.warn(
            "Trying to retrieve nhl ids from database for " +
            "game %s" % full_game_id)
        road_players, home_players = retrieve_player_ids_from_database(content)

    # finally adding retrieved player ids to recently downloaded game rosters
    doc = html.document_fromstring(content)
    # retrieving all table cells that contain a player's number
    rtds = get_table_cells(doc, 25, 'preceding')
    htds = get_table_cells(doc, 25, 'following')
    # rtds = doc.xpath(
    #     "//tr/td[@colspan='25']/parent::*/preceding-sibling::*/td" +
    #     "[@align='center' and @class='lborder + bborder + rborder']")
    # htds = doc.xpath(
    #     "//tr/td[@colspan='25']/parent::*/following-sibling::*/td" +
    #     "[@align='center' and @class='lborder + bborder + rborder']")

    logger.debug(
        "Number of road/home players found: %d/%d" % (len(rtds), len(htds)))

    if not rtds or not htds:
        logger.debug(
            "Couldn't retrieve team rosters by standard" +
            "method, trying alternative method")
        rtds = get_table_cells(doc, 22, 'preceding')
        htds = get_table_cells(doc, 22, 'following')

        # rtds = doc.xpath("//tr/td[@colspan='22']/parent::*/preceding-sibl
        # ing::*/td[@align='center' and @class='lborder + bborder + rborder']")
        # htds = doc.xpath("//tr/td[@colspan='22']/parent::*/following-sibl
        # ing::*/td[@align='center' and @class='lborder + bborder + rborder']")
        logger.debug(
            "Number of road/home players found via" +
            "alternative: %d/%d" % (len(rtds), len(htds)))

    # TODO: re-analyze what is done here
    for a in [rtds, htds]:
        if len(a) > 20:
            seen_numbers = list()
            tds_to_remove = list()
            for td in reversed(a):
                no = int(td.xpath("text()").pop())
                if no in seen_numbers:
                    logger.debug(
                        "Will remove table cell element from retrieved" +
                        "player numbers (game id: %s, raw_data: %s)" % (
                            full_game_id,
                            ", ".join(
                                td.xpath("following-sibling::td/text()"))))
                    tds_to_remove.append(td)
                    continue
                seen_numbers.append(no)
            else:
                [a.remove(tdr) for tdr in tds_to_remove]


def get_table_cells(doc, colspan, sibling_type):
    """
    Get table cells from specified parsed html document using the given colspan
    value and sibling type.
    """
    return doc.xpath(
        "//tr/td[@colspan='%d']/parent::*/%s-sib" % (colspan, sibling_type) +
        "ling::*/td[@align='center' and @class='lborder + bborder + rborder']")


def retrieve_player_ids_from_database(content):
    """
    Retrieves NHL player ids for all players listed in event summary from
    database.
    """
    # parsing raw HTML data into structured format
    game_report = html.document_fromstring(content)

    # retrieving player numbers and names from the game report raw data
    away_nos = game_report.xpath(
        "//tr/td[@colspan='25']/parent::*/preceding-sibling::*/td" +
        "[@align='center' and @class='lborder + bborder + rborder']")
    home_nos = game_report.xpath(
        "//tr/td[@colspan='25']/parent::*/following-sibling::*/td" +
        "[@align='center' and @class='lborder + bborder + rborder']")
    away_names = game_report.xpath(
        "//tr/td[@colspan='25']/parent::*/preceding-sibling::*/td" +
        "[@class='bborder + rborder']")
    home_names = game_report.xpath(
        "//tr/td[@colspan='25']/parent::*/following-sibling::*/td" +
        "[@class='bborder + rborder']")

    road_players = convert_names_numbers_to_players(away_names, away_nos)
    home_players = convert_names_numbers_to_players(home_names, home_nos)

    return road_players, home_players


def retrieve_player_ids_from_summary(summary):
    """
    Retrieves NHL player ids for all dressed players from JSON summary data
    provided by NHL stats API.
    """
    # setting up dictionary object to contain separate dictionaries with
    # jersey numbers as keys and player ids as values from 
    player_nos_by_team = dict()

    for home_away_type in ['home', 'away']:
        players_for_team = summary[
            'liveData']['boxscore']['teams'][home_away_type]
        # retrieving all player ids (skaters and goalies) first
        all_player_ids = set(
            players_for_team['skaters'] + players_for_team['goalies'])
        # retrieving ids of scratched players
        scratches_ids = set(players_for_team['scratches'])
        # deriving ids of all players dressed for current game
        dressed_ids = list(all_player_ids.difference(scratches_ids))

        team_player_no_dict = dict()

        # iterating over all collected player ids
        for nhl_id in dressed_ids:
            try:
                # retrieving jersey number of current player in current game
                no = int(
                    summary[
                        'liveData']['boxscore']['teams'][home_away_type][
                            'players']["ID%d" % nhl_id]["jerseyNumber"])
                # checking whether jersey number has already been used
                # (this shouldn't happen)
                if no in team_player_no_dict:
                    plr_already_inserted = Player.find_by_id(
                        team_player_no_dict[no])
                    plr_to_be_inserted = Player.find_by_id(nhl_id)
                    logger.warn(
                        "Jersey number %d used multiple times? " +
                        "(%s vs. %s)" % (
                            no, plr_already_inserted, plr_to_be_inserted))
                team_player_no_dict[no] = nhl_id
            except KeyError:
                logger.warn(
                    "JSON key 'jerseyNumber' not found for player with " +
                    "nhl_id %d." % nhl_id)
        else:
            player_nos_by_team[home_away_type] = team_player_no_dict

    return player_nos_by_team['away'], player_nos_by_team['home']


def retrieve_summary(full_game_id):
    """
    Retrieves JSON summary from NHL stats API using the specified game id.
    """
    try:
        url = JSON_SUMMARY_URL_TEMPLATE % full_game_id
        req = requests.get(url, params={'site': 'en_nhl'})
        logger.info(
            "Retrieving player nhl ids for game %s from %s" % (
                full_game_id, req.url))
        summary = json.loads(req.text)
    except:
        logger.warn(
            "Couldn't retrieve player nhl ids for game %s" % full_game_id)
        summary = None

    return summary


def convert_names_numbers_to_players(names, numbers):
    """
    Converting names and numbers retrieved from event summary to NHL player
    ids by searching database.
    """
    # extracting number, position, name and prename from event summary
    players = dict()
    for i in range(0, len(names), 2):
        # retrieving position
        position = names[i].xpath("text()")[0]

        # team penalties are listed in event summary
        # but only in the last line, i.e. it's safe to break from the
        # process here
        if position.upper() == 'TEAM PENALTY':
            break

        # retrieving name and prename (split by ',')
        last_name, first_name = names[i + 1].xpath("text()")[0].split(", ")
        # retrieving corresponding number from other list
        number = int(numbers.pop(0).xpath("text()")[0])

        # retrieving nhl id from database
        nhl_id = retrieve_nhl_id(last_name, first_name, position)

        players[number] = nhl_id

    return players


def retrieve_nhl_id(last_name, first_name, position):

    plr = Player.find_by_name(first_name, last_name)

    if plr is None:
        plr = Player.find_by_name_position(first_name, last_name, position)

    if plr is None:
        plr = Player.find_by_name_extended(first_name, last_name)

    if plr is None:
        logger.error(
            "Player not found in database: " +
            "%s %s (%s)" % (first_name, last_name, position))
        return 0
    else:
        return plr.nhl_id
