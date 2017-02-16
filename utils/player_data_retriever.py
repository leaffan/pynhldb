#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import itertools
import threading
import re

import requests
from dateutil import parser
from lxml import html

from db.common import session_scope
from db.team import Team
from db.player import Player
from db.player_season import PlayerSeason
from db.goalie_season import GoalieSeason
from db.player_data_item import PlayerDataItem
from utils import feet_to_m, lbs_to_kg

logger = logging.getLogger(__name__)


class PlayerDataRetriever():

    NHL_SITE_PREFIX = "http://statsapi.web.nhl.com/api/v1/people/"
    CAPFRIENDLY_PLAYER_PREFIX = "http://www.capfriendly.com/players/"
    CAPFRIENDLY_TEAM_PREFIX = "http://www.capfriendly.com/teams/"

    # input player data json keys
    JSON_KEY_FIRST_NAME = "firstName"
    JSON_KEY_LAST_NAME = "lastName"
    JSON_KEY_FULL_NAME = "fullName"
    JSON_KEY_POSITION = "primaryPosition"
    JSON_KEY_POSITION_CODE = "code"
    JSON_KEY_NUMBER = "primaryNumber"
    JSON_KEY_HEIGHT = "height"
    JSON_KEY_WEIGHT = "weight"
    JSON_KEY_HAND = "shootsCatches"
    JSON_KEY_DATE_OF_BIRTH = "birthDate"
    JSON_KEY_PLACE_OF_BIRTH_CITY = "birthCity"
    JSON_KEY_PLACE_OF_BIRTH_STATE_PROVINCE = "birthStateProvince"
    JSON_KEY_PLACE_OF_BIRTH_COUNTRY = "birthCountry"

    # database player data keys
    DB_KEY_FIRST_NAME = "first_name"
    DB_KEY_LAST_NAME = "last_name"
    DB_KEY_FULL_NAME = "full_name"
    DB_KEY_POSITION = "position"
    DB_KEY_NUMBER = "number"
    DB_KEY_HEIGHT_METRIC = "height_metric"
    DB_KEY_HEIGHT_IMPERIAL = "height_imperial"
    DB_KEY_WEIGHT_METRIC = "weight_metric"
    DB_KEY_WEIGHT_IMPERIAL = "weight_imperial"
    DB_KEY_HAND = "hand"
    DB_KEY_DATE_OF_BIRTH = "date_of_birth"
    DB_KEY_PLACE_OF_BIRTH = "place_of_birth"

    FT_IN_REGEX = re.compile("(\d+)'\s(\d+)")

    def __init__(self):
        self.lock = threading.Lock()

    def retrieve_player_seasons(self, player_id):
        """
        Retrieves player season statistics for player with specified id.
        """
        plr = Player.find_by_id(player_id)
        logger.info("+ Retrieving player season statistics for %s" % plr.name)

        plr_seasons = list()

        # retrieving raw season data for player_id
        plr_season_dict = self.retrieve_raw_season_data(player_id)

        if not plr_season_dict:
            return plr_seasons

        # extracting players' position
        plr_position = plr_season_dict.pop('position')

        for key in sorted(plr_season_dict.keys()):
            # keys are a tuple of season, season type, team count and team
            (season, season_type, season_team_sequence, team) = key
            season_data = plr_season_dict[key]

            if plr_position == 'G':
                plr_season = GoalieSeason(
                    player_id, season, season_type, team,
                    season_team_sequence, season_data)
                plr_season_db = GoalieSeason.find(
                    player_id, team, season, season_type, season_team_sequence)
            else:
                plr_season = PlayerSeason(
                    player_id, season, season_type, team,
                    season_team_sequence, season_data)
                plr_season_db = PlayerSeason.find(
                    player_id, team, season, season_type, season_team_sequence)

            plr_seasons.append(plr_season)

            self.create_or_update_database_item(plr_season, plr_season_db)

        logger.info(
            "+ %d season statistics items retrieved for %s" % (
                len(plr_seasons), plr.name))

        return plr_seasons

    def retrieve_player_data(self, player_id):
        """
        Retrieves personal data for player with specified id.
        """
        plr = Player.find_by_id(player_id)

        if plr is None:
            logger.warn("+ No player found for id: %d" % player_id)
            return

        logger.info("+ Retrieving player data for %s" % plr.name)

        plr_data_dict = self.retrieve_raw_season_data(player_id)

        plr_data_item = PlayerDataItem(player_id, plr_data_dict)
        plr_data_item_db = PlayerDataItem.find_by_player_id(player_id)

        self.create_or_update_database_item(plr_data_item, plr_data_item_db)

    def create_or_update_database_item(self, new_item, db_item):
        """
        Creates or updates a database item.
        """
        plr = Player.find_by_id(new_item.player_id)
        cls_name = new_item.__class__.__name__.lower()

        with session_scope() as session:
            if not db_item or db_item is None:
                logger.debug(
                    "\t+ Adding %s item for %s" % (cls_name, plr.name))
                session.add(new_item)
                return_item = new_item
            else:
                if db_item != new_item:
                    logger.info(
                        "\t+ Updating %s item for %s" % (cls_name, plr.name))
                    db_item.update(new_item)
                    return_item = session.merge(db_item)
                else:
                    return_item = db_item
            session.commit()

        return return_item

    def retrieve_raw_season_data(self, player_id):
        """
        Retrieves raw season statistics for specified player id from nhl.com.
        """
        url = "".join((self.NHL_SITE_PREFIX, str(player_id)))
        logger.debug(
            "+ Retrieving raw season statistics for player_id " +
            "%d from %s" % (player_id, url))
        r = requests.get(url, params={
            'expand': 'person.stats',
            'stats': 'yearByYear,yearByYearPlayoffs'})
        plr_json = r.json()

        plr_season_dict = dict()

        if 'people' not in plr_json:
            logger.warn(
                "+ Unable to retrieve raw season data for %s"
                % Player.find_by_id(player_id))
            return plr_season_dict

        for person in plr_json['people']:
            # retrieving players' primary position
            plr_season_dict['position'] = person['primaryPosition']['code']
            for stats_type in person['stats']:
                for split in stats_type['splits']:

                    # skipping any stat line that does not refer to the NHL
                    if split['league']['name'] != "National Hockey League":
                        continue

                    # retrieving season type for current stat line, i.e.
                    # regular season or playoffs
                    if stats_type['type']['displayName'] == "yearByYear":
                        season_type = 'RS'
                    elif stats_type['type']['displayName'] == "yearByYearPlayoffs":
                            season_type = 'PO'

                    # retrieving season and team of current statline
                    season = int(split['season'][:4])
                    team = Team.find_by_id(split['team']['id'])
                    # retrieving sequence number of current statline,
                    # important in case of a player playing for multiple teams
                    # in one season
                    season_team_sequence = split['sequenceNumber']

                    # adding current stat line to dictionary container
                    plr_season_dict[
                        (season, season_type, season_team_sequence, team)
                    ] = split['stat']

        return plr_season_dict

    def retrieve_raw_player_data(self, player_id):
        """
        Retrieves raw personal data for specified player id from nhl.com.
        """
        # retrieving player json page
        url = "".join((self.NHL_SITE_PREFIX, str(player_id)))
        r = requests.get(url)
        plr_json = r.json()

        plr_data_dict = dict()

        for person in plr_json['people']:
            # retrieving basic data (should be known already)
            plr_data_dict[
                self.DB_KEY_FIRST_NAME] = person[self.JSON_KEY_FIRST_NAME]
            plr_data_dict[
                self.DB_KEY_LAST_NAME] = person[self.JSON_KEY_LAST_NAME]
            plr_data_dict[
                self.DB_KEY_FULL_NAME] = person[self.JSON_KEY_FULL_NAME]
            plr_data_dict[
                self.DB_KEY_POSITION] = person[
                    self.JSON_KEY_POSITION][self.JSON_KEY_POSITION_CODE]

            # retrieving jersey number,...
            if self.JSON_KEY_NUMBER in person:
                plr_data_dict[
                    self.DB_KEY_NUMBER] = person[self.JSON_KEY_NUMBER]
            # height,...
            if self.JSON_KEY_HEIGHT in person:
                orig_height = person[self.JSON_KEY_HEIGHT]
                ft_in_regex_match = re.search(self.FT_IN_REGEX, orig_height)
                if ft_in_regex_match is not None:
                    feet = ft_in_regex_match.group(1)
                    inches = ft_in_regex_match.group(2)
                    height_metric = feet_to_m(feet, inches)
                    height_imperial = float(
                        "%d.%02d" % (int(feet), int(inches)))
                else:
                    height_metric = None
                    height_imperial = None
                plr_data_dict[self.DB_KEY_HEIGHT_METRIC] = height_metric
                plr_data_dict[self.DB_KEY_HEIGHT_IMPERIAL] = height_imperial
            # weight,...
            if self.JSON_KEY_WEIGHT in person:
                plr_data_dict[self.DB_KEY_WEIGHT_IMPERIAL] = person[
                    self.JSON_KEY_WEIGHT]
                # integer of rounded float value with zero decimals
                plr_data_dict[self.DB_KEY_WEIGHT_METRIC] = int(
                    round(lbs_to_kg(person[self.JSON_KEY_WEIGHT]), 0))
            # handedness,...
            if self.JSON_KEY_HAND in person:
                plr_data_dict[self.DB_KEY_HAND] = person[self.JSON_KEY_HAND]
            # date of birth,...
            if self.JSON_KEY_DATE_OF_BIRTH in person:
                plr_data_dict[self.DB_KEY_DATE_OF_BIRTH] = parser.parse(person[
                    self.JSON_KEY_DATE_OF_BIRTH]).date()  # just date component
            # place of birth
            if (
                self.JSON_KEY_PLACE_OF_BIRTH_CITY in person and
                self.JSON_KEY_PLACE_OF_BIRTH_COUNTRY in person
            ):
                if self.JSON_KEY_PLACE_OF_BIRTH_STATE_PROVINCE in person:
                    place_of_birth = ", ".join((
                        person[self.JSON_KEY_PLACE_OF_BIRTH_CITY],
                        person[self.JSON_KEY_PLACE_OF_BIRTH_STATE_PROVINCE],
                        person[self.JSON_KEY_PLACE_OF_BIRTH_COUNTRY]))
                else:
                    place_of_birth = ", ".join((
                        person[self.JSON_KEY_PLACE_OF_BIRTH_CITY],
                        person[self.JSON_KEY_PLACE_OF_BIRTH_COUNTRY]))
                plr_data_dict[self.DB_KEY_PLACE_OF_BIRTH] = place_of_birth

            # TODO: image retrieval

            if 'currentTeam' in person:
                plr_data_dict['current_team'] = person['currentTeam']['name']

        return plr_data_dict

    def collect_potential_capfriendly_ids(self, plr):
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

    def retrieve_capfriendly_ids(self, team_id):
        """
        Retrieves ids from capfriendly.com for all players of the team with
        the specified id
        """
        team = Team.find_by_id(team_id)

        logger.info(
            "+ Retrieving capfriendly ids for all players of the %s" % team)

        url = "".join((
            self.CAPFRIENDLY_TEAM_PREFIX,
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
                print(first_name, last_name, plr, player_link.split("/")[-1])
            if plr is None:
                print("\t", first_name, last_name, player_link.split("/")[-1])

    def retrieve_capfriendly_id(self, player_id):
        """
        Retrieves an id from capfriendly.com for the player with the
        specified id.
        """
        plr = Player.find_by_id(player_id)

        if plr.capfriendly_id is not None:
            logger.info(
                "+ Existing capfriendly id for %s: %s" % (
                    plr.name, plr.capfriendly_id))
            return plr.capfriendly_id

        # compiling all potential capfriendly ids from the player's name(s)
        potential_capfriendly_ids = self.collect_potential_capfriendly_ids(plr)

        capfriendly_id_found = False

        while potential_capfriendly_ids and not capfriendly_id_found:
            potential_capfriendly_id = potential_capfriendly_ids.pop(0)
            query_id = potential_capfriendly_id.replace(" ", "-")
            url = "".join((self.CAPFRIENDLY_PLAYER_PREFIX, query_id))
            r = requests.get(url)
            doc = html.fromstring(r.text)
            page_header = doc.xpath("//h1/text()").pop(0).strip()
            if page_header == potential_capfriendly_id.upper():
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
