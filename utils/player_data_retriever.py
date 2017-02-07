#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import threading
import re

import requests
from dateutil import parser

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
    CAPFRIENDLY_SITE_PREFIX = "http://www.capfriendly.com/players/"

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

    def retrieve_player_data(self, player_id, simulation=False):
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

        if not simulation:
            self.create_or_update_player_data(plr_data_item, plr_data_item_db)

    def create_or_update_player_season(self, plr_season, plr_season_db):
        """
        Creates or updates a player season database object.
        """
        with session_scope() as session:
            if not plr_season_db or plr_season_db is None:
                logger.debug("+ Adding season statistics: %s" % plr_season)
                session.add(plr_season)
            else:
                if plr_season_db != plr_season:
                    logger.info(
                        "+ Updating season statistics: %s" % plr_season)
                    plr_season_db.update(plr_season)
                    session.merge(plr_season_db)
            session.commit()

    def create_or_update_player_data(self, plr_data, plr_data_db):
        """
        Creates or updates a player data item database object.
        """
        plr = Player.find_by_id(plr_data.player_id)

        with session_scope() as session:
            if not plr_data_db or plr_data_db is None:
                logger.debug("+ Adding player data for %s" % plr.name)
                session.add(plr_data)
            else:
                if plr_data_db != plr_data:
                    logger.info("+ Updating player data for %s" % plr.name)
                    plr_data_db.update(plr_data)
                    session.merge(plr_data_db)
            session.commit()

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

            # TODO: image retrieval

            if 'currentTeam' in person:
                plr_data_dict['current_team'] = person['currentTeam']['name']

        return plr_data_dict

    def retrieve_raw_contract_data(self, player_id):

        from lxml import html

        plr = Player.find_by_id(player_id)
        print(plr.name)

        url = "".join(
            (self.CAPFRIENDLY_SITE_PREFIX, plr.name.replace(" ", "-").lower()))

        r = requests.get(url)
        doc = html.fromstring(r.text)

        ct_data = doc.xpath("//div[@class='column_head3 rel cntrct']")

        for ct in ct_data:
            ct_length, exp_status, sign_team = ct.xpath(
                "div/div[@class='l cont_t mt4 mb2']/text()")
            ct_value, dummy, cap_hit_pct, sign_date, ct_source = ct.xpath(
                "div/div[@class='l cont_t mb5']/text()")
            raw_ct_years_trs = ct.xpath(
                "following-sibling::table/tbody/tr[@class='even' or @class='odd']")

            ct_lenth_regex = re.compile("LENGTH\:\s(\d+)\sYEARS?")
            ct_length = int(re.search(ct_lenth_regex, ct_length).group(1))

            exp_status = exp_status.split()[-1]

            sign_team = Team.find_by_name(sign_team.split(":")[-1].strip())

            ct_value = int(ct_value.split(":")[-1].strip()[1:].replace(",", ""))

            cap_hit_pct = float(cap_hit_pct.split()[-1])

            try:
                sign_date = parser.parse(sign_date.split(":")[-1]).date()
            except ValueError:
                sign_date = None

            ct_source = ct_source.split()[-1]

            for tr in raw_ct_years_trs:
                self.retrieve_contract_year(tr)
                # print(tr.xpath("td"))
                # print(len(tr), "...", tr.xpath("td/text()"))
                # print("...")

            # print(raw_ct_years)

        print()

    def retrieve_contract_year(self, raw_contract_year_data):

        tds = raw_contract_year_data.xpath("td")

        if len(tds) == 8:
            season = int(tds[0].xpath("text()")[0].split("-")[0])
            if tds[1].xpath("text()"):
                clause = tds[1].xpath("text()").pop(0)
            else:
                clause = None
            cap_hit = int(tds[2].xpath("text()").pop(0)[1:].replace(",", ""))
            aav = int(tds[3].xpath("text()").pop(0)[1:].replace(",", ""))
            sign_bonus = int(tds[4].xpath("text()").pop(0)[1:].replace(",", ""))
            perf_bonus = int(tds[5].xpath("text()").pop(0)[1:].replace(",", ""))
            nhl_salary = int(tds[6].xpath("text()").pop(0)[1:].replace(",", ""))
            minors_salary = int(tds[7].xpath("text()").pop(0)[1:].replace(",", ""))


            print(season, clause, cap_hit, aav, sign_bonus, perf_bonus, nhl_salary, minors_salary)
