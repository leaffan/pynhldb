#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
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
from db.contract import Contract
from db.contract_year import ContractYear
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
    CT_LENGTH_REGEX = re.compile("LENGTH\:\s(\d+)\sYEARS?")

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
                self.create_or_update_database_item(plr_season, plr_season_db)

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
            self.create_or_update_database_item(
                plr_data_item, plr_data_item_db)

    def retrieve_player_contracts(self, player_id, simulation=False):
        plr = Player.find_by_id(player_id)

        if plr is None:
            logger.warn("+ No player found for id: %d" % player_id)
            return

        logger.info("+ Retrieving player contracts for %s" % plr.name)

        plr_contract_list = self.retrieve_raw_contract_data(player_id)

        for plr_contract_dict in plr_contract_list:
            print(plr_contract_dict.keys())
            contract = Contract(player_id, plr_contract_dict)
            contract_db = Contract.find(
                player_id,
                plr_contract_dict['start_season'],
                plr_contract_dict['end_season'])

            if not simulation:
                self.create_or_update_database_item(contract, contract_db)

            if not contract_db:
                continue

            print(plr_contract_dict['contract_years'])


    def create_or_update_database_item(self, new_item, db_item):
        """
        Creates or updates database item.
        """
        plr = Player.find_by_id(new_item.player_id)

        if type(new_item) is Contract:
            ss = 'contract'
        elif type(new_item) is ContractYear:
            ss = 'contract year'
        elif type(new_item) is PlayerSeason:
            ss = 'player season'
        elif type(new_item) is PlayerDataItem:
            ss = 'player data'
        else:
            ss = ''

        with session_scope() as session:
            if not db_item or db_item is None:
                logger.debug("+ Adding %s item for %s" % (ss, plr.name))
                session.add(new_item)
            else:
                if db_item != new_item:
                    logger.info("+ Updating %s item for %s" % (ss, plr.name))
                    db_item.update(new_item)
                    session.merge(db_item)
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

        plr = Player.find_by_id(player_id)

        url = "".join(
            (self.CAPFRIENDLY_SITE_PREFIX, plr.name.replace(" ", "-").lower()))
        r = requests.get(url)
        doc = html.fromstring(r.text)

        contract_elements = doc.xpath(
            "//div[@class='column_head3 rel cntrct']")
        historical_data = doc.xpath(
            "//div[@class='rel navc column_head3 cntrct']")

        contract_list = list()

        for element in contract_elements:
            contract_dict = dict()

            # retrieving raw contract length, expiry status and signing team
            ct_length, exp_status, sign_team = element.xpath(
                "div/div[@class='l cont_t mt4 mb2']/text()")
            # retrieving raw contract value, cap hit percentatge, signing date
            # and source
            ct_value, _, cap_hit_pct, sign_date, ct_source = element.xpath(
                "div/div[@class='l cont_t mb5']/text()")
            # retrieving raw contract years
            raw_ct_years_trs = element.xpath(
                "following-sibling::table/tbody/tr[@class='even' or @class='odd']")

            # retrieving contract type, i.e. standard, entry level or 35+
            contract_dict['type'] = element.xpath("div/h6/text()").pop(0)
            # retrieving contract length
            contract_dict['length'] = int(
                re.search(self.CT_LENGTH_REGEX, ct_length).group(1))
            # retrieving player status after contract expires
            contract_dict['expiry_status'] = exp_status.split()[-1]
            # retrieving id of signing team
            sign_team = Team.find_by_name(sign_team.split(":")[-1].strip())
            if sign_team:
                sign_team_id = sign_team.team_id
            else:
                sign_team_id = None
            contract_dict['signing_team_id'] = sign_team_id
            # retrieving overall contract value
            contract_dict['value'] = int(
                ct_value.split(":")[-1].strip()[1:].replace(",", ""))
            # retrieving cap hit percentage
            contract_dict['cap_hit_percentage'] = float(
                cap_hit_pct.split()[-1])
            # retrieving source for contract data
            contract_dict['source'] = ct_source.split(":")[-1].strip()
            # retrieving contract signing date
            try:
                sign_date = parser.parse(sign_date.split(":")[-1]).date()
            except ValueError:
                sign_date = None
            contract_dict['signing_date'] = sign_date

            seasons, contract_years = self.retrieve_raw_contract_years_for_contract(raw_ct_years_trs)

            # retrieving first and last season of the contract from
            contract_dict['start_season'] = min(seasons)
            contract_dict['end_season'] = max(seasons)
            # adding raw contract years to resulting dictionary
            contract_dict['contract_years'] = contract_years

            contract_list.append(contract_dict)

        return contract_list

    def retrieve_raw_contract_years_for_contract(self, raw_contract_years_trs):
            seasons = list()
            contract_years = list()

            for tr in raw_contract_years_trs:
                ct_year_dict = self.retrieve_contract_year(tr)
                seasons.append(ct_year_dict['season'])
                contract_years.append(ct_year_dict)

            return seasons, contract_years

    def retrieve_contract_year(self, raw_contract_year_data):

        ct_year_dict = dict()
        # retrieving table cells from current html table row
        tds = raw_contract_year_data.xpath("td")

        # retrieving first year in season identifier
        ct_year_dict['season'] = int(tds[0].xpath("text()")[0].split("-")[0])

        # if there are just two table cells, this is historical salary data
        # from before the 2004-05 lockout
        if len(tds) == 2:
            ct_year_dict['nhl_salary'] = int(
                tds[-1].xpath("text()").pop(0)[1:].replace(",", ""))
            return ct_year_dict

        # if there are just three table cells, we're usually dealing with
        # a contract year nixed by the 2004-05 lockout
        if len(tds) == 3:
            ct_year_dict['note'] = tds[-1].xpath("text()").pop(0)
            return ct_year_dict

        # retrieving (no trade, no movement) clause for contract year
        # (if available)
        if tds[1].xpath("text()"):
            ct_year_dict['clause'] = tds[1].xpath("text()").pop(0)

        # items 2 to 4 are cap hit, annual average value (aav) and signing
        # bonus
        idx = 2
        for item in ['cap_hit', 'aav', 'sign_bonus']:
            ct_year_dict[item] = int(
                tds[idx].xpath("text()").pop(0)[1:].replace(",", ""))
            idx += 1

        # if there are just six table cells, we're usually dealing with
        # an entry-level contract slide
        if len(tds) == 6:
            ct_year_dict['note'] = tds[-1].xpath("text()").pop(0)
            return ct_year_dict

        # items 5 to 7 are performance bonus, nhl salary and minor
        # league salary
        idx = 5
        for item in ['perf_bonus', 'nhl_salary', 'minors_salary']:
            ct_year_dict[item] = int(
                tds[idx].xpath("text()").pop(0)[1:].replace(",", ""))
            idx += 1

        return ct_year_dict
