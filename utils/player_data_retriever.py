#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import threading

import requests

from db.common import session_scope
from db.team import Team
from db.player import Player
from db.player_season import PlayerSeason
from db.goalie_season import GoalieSeason
from utils import feet_to_cm

logger = logging.getLogger(__name__)


class PlayerDataRetriever():

    NHL_SITE_PREFIX = "http://statsapi.web.nhl.com/api/v1/people/"

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
    DB_KEY_HEIGHT = "height"
    DB_KEY_WEIGHT = "weight"
    DB_KEY_HAND = "hand"
    DB_KEY_DATE_OF_BIRTH = "date_of_birth"
    DB_KEY_PLACE_OF_BIRTH = "place_of_birth"

    def __init__(self):
        self.lock = threading.Lock()

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

    def create_or_update_player_season(self, plr_season, plr_season_db):
        """
        Creates or updates a player season database object.
        """
        with session_scope() as session:
            if not plr_season_db or plr_season_db is None:
                logger.debug("Adding season statistics: %s" % plr_season)
                session.add(plr_season)
            else:
                if plr_season_db != plr_season:
                    logger.info("Updating season statistics: %s" % plr_season)
                    plr_season_db.update(plr_season)
                    session.merge(plr_season_db)
            session.commit()

    def retrieve_player_seasons(self, player_id, simulation=False):
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

            if not simulation:
                self.create_or_update_player_season(plr_season, plr_season_db)

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

        logger.info("+ Retrieving player season statistics for %s" % plr.name)

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
                height = person[self.JSON_KEY_HEIGHT]
                if len(height.split()) > 1:
                    (feet, inches) = height.split()
                    height = feet_to_cm(feet, inches)
                else:
                    height = None
                plr_data_dict[self.DB_KEY_HEIGHT] = height
            # weight,...
            if self.JSON_KEY_WEIGHT in person:
                plr_data_dict[self.DB_KEY_WEIGHT] = person[
                    self.JSON_KEY_WEIGHT]
            # handedness,...
            if self.JSON_KEY_HAND in person:
                plr_data_dict[self.DB_KEY_HAND] = person[self.JSON_KEY_HAND]
            # date of birth,...
            if self.JSON_KEY_DATE_OF_BIRTH in person:
                plr_data_dict[self.DB_KEY_DATE_OF_BIRTH] = person[
                    self.JSON_KEY_DATE_OF_BIRTH]
            # place of birth
            if self.JSON_KEY_PLACE_OF_BIRTH_CITY in person and self.JSON_KEY_PLACE_OF_BIRTH_COUNTRY in person:
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

            plr_data_dict['current_team'] = person['currentTeam']['name']

            print(plr_data_dict)
