#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging

import requests
from lxml import html, etree

from db.player import Player

logger = logging.getLogger(__name__)

JSON_SUMMARY_URL_TEMPLATE = "https://api-web.nhle.com/v1/gamecenter/%s/play-by-play"


def add_nhl_ids_to_content(url, content):
    """
    Adds player ids used by nhl.com to each roster player on event summary
    to allow for a unique identification later on.
    """
    # retrieving current season and game id from specified url
    season = int(os.path.dirname(url).split("/")[-1][:4])
    game_id = os.path.basename(url).split(".")[0][2:]

    # setting up fully qualified game id to be used in boxscore url
    full_game_id = "%d%s" % (season, game_id)
    # retrieving json summary from  NHL stats API
    summary = retrieve_summary(full_game_id)

    # if json boxscore is valid, use it to retrieve nhl player ids from it
    if summary and 'rosterSpots' in summary.keys():
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
    # parsing html content into document tree first
    doc = html.document_fromstring(content)
    for players, sibling_type in zip(
            [road_players, home_players], ['preceding', 'following']):
        # retrieving all table cells that contain a player's number
        tds = get_table_cells(doc, sibling_type)
        # inserting player id in span element behind player's numbers
        insert_nhl_ids(tds, players)

    return etree.tostring(doc, method='html', pretty_print=True)


def insert_nhl_ids(tds, players):
    """
    Insert nhl ids for each player into the according team's html roster
    representation.
    """
    # modifying each of the specified table cells
    for td in tds:
        # retrieving player's jersey number from current table cell
        no = int(td.text_content())
        # trying to retrieve player id from player dictionary
        try:
            nhl_id = players[no]
        # otherwise retrieving player id from database
        except KeyError:
            # retrieving player position and full name from current table cell
            position, name = td.xpath("following-sibling::*//text()")[:2]
            # splitting up full name into first and last name
            last_name, first_name = [x.strip() for x in name.split(",")]
            # finding player by first and last name as well as position in db
            nhl_id = retrieve_player_id(last_name, first_name, position)

        # TODO: find player on website and create it if not found in database

        # creating a span element using the attribute 'nhl_id' with the
        # current player's id as value
        span = etree.Element("span", nhl_id=str(nhl_id))
        # inserting newly created span element into the document tree
        td.insert(0, span)


def get_table_cells(doc, sibling_type):
    """
    Get table cells from specified parsed html document using the given colspan
    value and sibling type.
    """
    # retrieving all table cells above or below a table cell spanning the whole
    # table width
    tds = doc.xpath(
        "//tr/td[@colspan='22' or @colspan='25']/parent::*/" +
        "%s-sibling::*/td[@align='center' and @class='lborder" % sibling_type +
        " + bborder + rborder']")

    # making sure no additional goaltender summary table cells are among
    # the ones retrieved above by adding them to a dictionary using the
    # jersey numbers as keys
    distinct_table_cells = {int(td.xpath("text()").pop()): td for td in tds}

    # returning the dicionary values, i.e. unique table cells
    return list(distinct_table_cells.values())


def retrieve_player_ids_from_database(content):
    """
    Retrieves NHL player ids for all players listed in event summary from
    database.
    """
    # parsing raw HTML data into structured format
    game_report = html.document_fromstring(content)

    # retrieving player numbers and names from the game report raw data
    # TODO: check xpath expressions for general validity
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
    player_nos_by_team['home'] = dict()
    player_nos_by_team['away'] = dict()

    for plr in summary['rosterSpots']:
        if plr['teamId'] == summary['homeTeam']['id']:
            player_nos_by_team['home'][plr['sweaterNumber']] = plr['playerId']
        elif plr['teamId'] == summary['awayTeam']['id']:
            player_nos_by_team['away'][plr['sweaterNumber']] = plr['playerId']

    return player_nos_by_team['away'], player_nos_by_team['home']


def retrieve_summary(full_game_id):
    """
    Retrieves JSON summary from NHL stats API using the specified game id.
    """
    try:
        url = JSON_SUMMARY_URL_TEMPLATE % full_game_id
        req = requests.get(url, params={'site': 'en_nhl'})
        logger.info(f"Retrieving player nhl ids for game {full_game_id} from {req.url}")
        summary = json.loads(req.text)
    except:
        logger.warn(f"Couldn't retrieve player nhl ids for game {full_game_id}")
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
        nhl_id = retrieve_player_id(last_name, first_name, position)

        players[number] = nhl_id

    return players


def retrieve_player_id(last_name, first_name, position):
    """
    Retrieve player id from database for player specified by first and name as
    well as position.
    """

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
        return plr.player_id
