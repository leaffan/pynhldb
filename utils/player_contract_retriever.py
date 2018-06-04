#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re

import requests
from dateutil import parser
from lxml import html

# from db import create_or_update_db_item
from db.common import session_scope
from db.player import Player
from db.team import Team
from db.contract import Contract
from db.contract_year import ContractYear
from db.buyout import Buyout
from db.buyout_year import BuyoutYear

logger = logging.getLogger(__name__)


class PlayerContractRetriever():

    CAPFRIENDLY_PLAYER_PREFIX = "http://www.capfriendly.com/players/"
    CAPFRIENDLY_TEAM_PREFIX = "http://www.capfriendly.com/teams/"
    CAPFRIENDLY_CLAUSE_REGEX = re.compile("^\:\s")
    CAPFRIENDLY_AMOUNT_REGEX = re.compile("\$|\-|,|\u2013")
    CT_LENGTH_REGEX = re.compile("LENGTH\:\s(\d+)\sYEARS?")
    EXPIRY_STATUS_REGEX = re.compile("(UFA \(NO QO\))|(RFA)|(UFA)")

    def __init__(self):
        pass

    def retrieve_player_contracts(self, player_id):
        """
        Retrieves comprehensive contract information for player with specified
        id, including buyouts and historical salary data.
        """
        plr = Player.find_by_id(player_id)

        if plr is None:
            logger.warn("+ No player found for id: %d" % player_id)
            return

        logger.info("+ Retrieving player contracts for %s" % plr.name)

        # retrieving raw, i.e. list of dictionaries, contract and historical
        # salary information
        plr_contract_list = self.retrieve_raw_contract_data(player_id)
        historical_salaries = self.retrieve_raw_historical_salary_data(
            player_id)

        # creating or updating contract database item
        for plr_contract_dict in plr_contract_list:
            contract = Contract(player_id, plr_contract_dict)
            contract_db = Contract.find_with_team(
                player_id,
                plr_contract_dict['start_season'],
                plr_contract_dict['signing_team_id'])

            contract_db = self.create_or_update_database_item(
                contract, contract_db)

            # creating/retrieving buyout item in/from database (if applicable
            # to current contract)
            if contract_db.bought_out:
                buyout = self.retrieve_buyout(player_id, contract_db)
            else:
                buyout = None

            # creating or updating contract years in database
            for contract_year_dict in plr_contract_dict['contract_years']:
                # adding buyout flag to contract year if buyout happened in
                # this or prior seasons
                if buyout:
                    if contract_year_dict['season'] >= buyout.start_season:
                        contract_year_dict['bought_out'] = True
                contract_year = ContractYear(
                    player_id, contract_db.contract_id, contract_year_dict)
                contract_year_db = ContractYear.find(
                    player_id, contract_db.contract_id,
                    contract_year_dict['season'])
                self.create_or_update_database_item(
                    contract_year, contract_year_db)

        # creating or updating historical salary data in database
        for hist_salary_year in historical_salaries:
            contract_year = ContractYear(player_id, None, hist_salary_year)
            contract_year_db = ContractYear.find(
                player_id, None, hist_salary_year['season'])
            self.create_or_update_database_item(
                contract_year, contract_year_db)

    def retrieve_buyout(self, player_id, contract):
        """
        Retrieves buyout information for specified player and contract.
        """
        # retrieving raw buyout data
        buyout_dict = self.retrieve_raw_buyout_data(player_id)
        # setting up buyout item
        buyout = Buyout(player_id, contract.contract_id, buyout_dict)
        # finding suitable buyout in database
        buyout_db = Buyout.find(contract.contract_id)
        # creating (or updating) buyout in database
        buyout_db = self.create_or_update_database_item(buyout, buyout_db)
        # adding buyout years to buyout
        for buyout_year_data_dict in buyout_dict['buyout_years']:
            # setting up buyout year item
            buyout_year = BuyoutYear(
                player_id, buyout_db.buyout_id, buyout_year_data_dict)
            # finding suitable buyout year in database
            buyout_year_db = BuyoutYear.find(
                buyout_db.buyout_id, buyout_year_data_dict['season'])
            # creating or updating buyout year
            buyout_year_db = self.create_or_update_database_item(
                buyout_year, buyout_year_db)
        return buyout_db

    def retrieve_raw_contract_data_by_capfriendly_id(self, capfriendly_id):
        """
        Retrieves raw contract information for player with specified
        capfriendly id as a list of dictionary objects.
        """
        # setting up list of contracts for current player
        contract_list = list()

        url = "".join((self.CAPFRIENDLY_PLAYER_PREFIX, capfriendly_id))
        r = requests.get(url)
        doc = html.fromstring(r.text)

        contract_elements = doc.xpath(
            "//div[@class='column_head3 rel cntrct']")

        for element in contract_elements:
            # setting up dictionary for current contract
            contract_dict = dict()
            # retrieving raw contract length, expiry status and signing team
            # as list of text elements
            raw_length_exp_status_sign_team = element.xpath(
                "div/div[@class='l cont_t mt4 mb2']/" +
                "descendant-or-self::*/text()")
            # retrieving raw contract length from first entry in previously
            # created list
            ct_length = raw_length_exp_status_sign_team[0]
            # retrieving expiry status from various entries in previously
            # created list (dependant on potential additional information)
            if len(raw_length_exp_status_sign_team) == 3:
                exp_status = raw_length_exp_status_sign_team[1]
            else:
                exp_status = "".join(raw_length_exp_status_sign_team[1:4])
            # retrieving signing team separately from last entry in previously
            # created list
            sign_team = raw_length_exp_status_sign_team[-1]
            # retrieving raw contract value, cap hit percentage, signing date
            # and source
            raw_value_cap_hit_pct_date_source = element.xpath(
                "div/div[@class='l cont_t mb5']/text()")
            if len(raw_value_cap_hit_pct_date_source) == 5:
                ct_value, _, cap_hit_pct, sign_date, ct_source = (
                    raw_value_cap_hit_pct_date_source)
            # at times we're trying to retrieve basic contract data even w/o
            # a verified source, e.g. for contracts signed very recently
            else:
                ct_value, _, cap_hit_pct, sign_date = (
                    raw_value_cap_hit_pct_date_source
                )
                ct_source = ""
            # retrieving raw contract notes
            ct_notes = element.xpath(
                "following-sibling::div[contains(@class, 'clause')]/" +
                "descendant-or-self::*/text()")
            # retrieving table rows with raw contract years
            raw_ct_years_trs = element.xpath(
                "following-sibling::table/tbody/" +
                "tr[@class='even' or @class='odd']")
            # retrieving contract notes, i.e. buyout notifications or clause
            # details
            contract_dict['notes'] = self.get_contract_notes(ct_notes)
            # setting buyout flag
            contract_dict['bought_out'] = self.get_contract_buyout_status(
                contract_dict)
            # retrieving contract type, i.e. standard, entry level or 35+
            contract_dict['type'] = element.xpath("div/h6/text()").pop(0)
            # retrieving contract length
            contract_dict['length'] = int(
                re.search(self.CT_LENGTH_REGEX, ct_length).group(1))
            # retrieving player status after contract expires, e.g. RFA, UFA
            # or UFA (NO QO)
            contract_dict['expiry_status'] = re.search(
                self.EXPIRY_STATUS_REGEX, exp_status).group(0)
            # retrieving id of signing team
            contract_dict[
                'signing_team_id'] = self.get_contract_buyout_signing_team(
                    sign_team)
            # retrieving overall contract value
            contract_dict['value'] = int(
                ct_value.split(":")[-1].strip()[1:].replace(",", ""))
            # retrieving cap hit percentage
            contract_dict['cap_hit_percentage'] = float(
                cap_hit_pct.split()[-1])
            # retrieving source for contract data
            contract_dict['source'] = ct_source.split(":")[-1].strip()
            # retrieving contract signing date
            contract_dict['signing_date'] = self.get_contract_buyout_date(
                sign_date)

            # retrieving seasons and contract years
            seasons, contract_years = self.retrieve_raw_contract_years(
                raw_ct_years_trs)

            # retrieving first and last season of the contract from
            contract_dict['start_season'] = min(seasons)
            contract_dict['end_season'] = max(seasons)
            # adding raw contract years to resulting dictionary
            contract_dict['contract_years'] = contract_years

            # adding current contract to list of all current players' contracts
            contract_list.append(contract_dict)

        return contract_list

    def retrieve_raw_contract_data(self, player_id):
        """
        Retrieves raw contract information for player with specified database
        id as a list of dictionary objects.
        """
        plr = Player.find_by_id(player_id)
        if plr.capfriendly_id is None:
            logger.warn("+ Unable to retrieve contract data for %s" % plr.name)
            return list()

        return self.retrieve_raw_contract_data_by_capfriendly_id(
            plr.capfriendly_id)

    def retrieve_raw_historical_salary_data(self, player_id):
        """
        Retrieves historical salary, i.e. predominantly pre salary cap
        information for player with specified id as a list of dictionary
        objects.
        """
        # setting up list of historical salaries for current player
        historical_salaries = list()

        plr = Player.find_by_id(player_id)
        if plr.capfriendly_id is None:
            logger.warn(
                "+ Unable to retrieve historical salary " +
                "data for %s" % plr.name)
            return historical_salaries

        url = "".join((self.CAPFRIENDLY_PLAYER_PREFIX, plr.capfriendly_id))
        r = requests.get(url)
        doc = html.fromstring(r.text)

        hist_elements = doc.xpath(
            "//div[@class='rel navc column_head3 cntrct']")

        for element in hist_elements:
            # retrieving table rows with historical per-year salaries
            raw_hist_salary_years = element.xpath(
                "following-sibling::table/tbody/tr" +
                "[@class='even' or @class='odd']")

            for tr in raw_hist_salary_years:
                historical_salary = dict()
                # sometimes there is no historical salary data for a season
                try:
                    season, salary = tr.xpath("td/text()")
                except ValueError:
                    logger.warn(
                        "+ Unable to retrieve historical salary " +
                        "of %s for season %s" % (
                            plr.name, tr.xpath("td/text()")[0]))
                    continue
                season = int(season.split("-")[0])
                # for the 2004-05 lockout table data does not contain a
                # numerical value
                try:
                    salary = int(salary[1:].replace(",", ""))
                except ValueError:
                    logger.warn(
                        "+ Unable to retrieve numeric value " +
                        "from '%s'" % salary)
                    continue
                historical_salary['season'] = season
                historical_salary['nhl_salary'] = salary

                historical_salaries.append(historical_salary)

        return historical_salaries

    def retrieve_raw_contract_years(self, raw_contract_years_trs):
        seasons = list()
        contract_years = list()

        for tr in raw_contract_years_trs:
            ct_year_dict = self.retrieve_contract_year(tr)
            seasons.append(ct_year_dict['season'])
            contract_years.append(ct_year_dict)

        return seasons, contract_years

    def retrieve_raw_buyout_data(self, player_id):
        """
        Retrieves buyout information for player with specified id as a
        dictionary object.
        """
        buyout_dict = dict()

        plr = Player.find_by_id(player_id)
        if plr.capfriendly_id is None:
            logger.warn("+ Unable to retrieve contract data for %s" % plr.name)
            return buyout_dict

        url = "".join((self.CAPFRIENDLY_PLAYER_PREFIX, plr.capfriendly_id))
        r = requests.get(url)
        doc = html.fromstring(r.text)

        # retrieving raw length, value and team of buyout
        buyout_length, buyout_team = doc.xpath(
            "//div[@class='mt4 mb2']/div[@class='l cont_t']/text()")
        buyout_value, buyout_date = doc.xpath(
            "//div[@class='mt2 mb4 cb']/div[@class='l cont_t']/text()")

        # retrieving buyout length
        buyout_dict['length'] = int(
            re.search(self.CT_LENGTH_REGEX, buyout_length).group(1))
        # retrieving buyout value
        buyout_dict['value'] = int(
            buyout_value.split(":")[-1].strip()[1:].replace(",", ""))
        # retrieving id of buyout team
        buyout_dict['buyout_team_id'] = self.get_contract_buyout_signing_team(
            buyout_team)
        buyout_dict['buyout_date'] = self.get_contract_buyout_date(
            buyout_date)

        # retrieving table rows each representing a year of the buyout
        raw_buyout_years = doc.xpath(
            "//div[@class='mt4 mb2']/ancestor::div/" +
            "following-sibling::table/tbody/tr[@class='even' or @class='odd']")

        buyout_years = list()

        for raw_buyout_year in raw_buyout_years:
            buyout_year_dict = dict()
            season, cost, cap_hit = raw_buyout_year.xpath("td/text()")
            # retrieving first year in season identifier
            buyout_year_dict['season'] = int(season.split("-")[0])
            # retrieving buyout cost
            buyout_year_dict['cost'] = int(cost.strip()[1:].replace(",", ""))
            # retrieving buyout cap hit
            buyout_year_dict['cap_hit'] = int(
                cap_hit.replace(",", "").replace("$", "").strip())
            buyout_years.append(buyout_year_dict)

        buyout_dict['buyout_years'] = buyout_years
        buyout_dict['start_season'] = min(
            [buyout_year['season'] for buyout_year in buyout_years])
        buyout_dict['end_season'] = max(
            [buyout_year['season'] for buyout_year in buyout_years])

        return buyout_dict

    def retrieve_contract_year(self, raw_contract_year_data):
        """
        Retrieves single contract year item using the specified raw data.
        """
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

        # table cell items 2 through 5 represent cap hit, annual average value
        # (aav) and performance as well as signing bonus
        idx = 2
        for item in ['cap_hit', 'aav', 'perf_bonus', 'sign_bonus']:
            raw_value = re.sub(
                self.CAPFRIENDLY_AMOUNT_REGEX, "", tds[idx].xpath(
                    "text()").pop(0))
            if raw_value:
                ct_year_dict[item] = int(raw_value)
            idx += 1

        # checking last table cell for indication of an entry-level slide
        if tds[-1].xpath("*/text()[contains(., 'ENTRY-LEVEL SLIDE')]"):
            ct_year_dict['note'] = tds[-1].xpath("*/text()").pop(0)
            return ct_year_dict

        # otherwise last two table cell items represent total nhl salary and
        # minor league salary
        idx = -2
        for item in ['nhl_salary', 'minors_salary']:
            ct_year_dict[item] = int(
                tds[idx].xpath("text()").pop(0)[1:].replace(",", ""))
            idx += 1

        return ct_year_dict

    def get_contract_notes(self, raw_contract_notes):
        """
        Gets database-ready contract notes from specfied raw contract notes.
        """
        contract_notes = list()
        for note in raw_contract_notes:
            check_note = note.replace(":", "").strip().upper()
            if check_note == "CONTRACT NOTE":
                continue
            if check_note == "CLAUSE DETAILS":
                continue
            if (
                check_note == "CLAUSE SOURCE" or check_note.startswith(
                    "CLAUSE SOURCE")):
                continue
            note = re.sub(self.CAPFRIENDLY_CLAUSE_REGEX, "", note)
            if note:
                contract_notes.append(note)
        return ", ".join(contract_notes)

    def get_contract_buyout_status(self, contract_dict):
        """
        Gets buyout status for contract contained by specified dictionary.
        """
        # by default contracts are not bought out
        buyout_status = False
        # but some are, it's then marked in the contract notes
        if 'notes' in contract_dict:
            if "Contract was bought out".lower() in contract_dict['notes']:
                buyout_status = True
        return buyout_status

    def get_contract_buyout_signing_team(self, sign_team_info):
        """
        Gets actual team object from specified raw data.
        """
        sign_team = Team.find_by_name(sign_team_info.split(":")[-1].strip())
        if sign_team:
            return sign_team.team_id
        else:
            return None

    def get_contract_buyout_date(self, sign_date_info):
        """
        Gets contract signing date from specified raw data.
        """
        try:
            return parser.parse(sign_date_info.split(":")[-1]).date()
        except ValueError:
            logger.warn("+ Unable to parse date from '%s'" % sign_date_info)
            return None

    def create_or_update_database_item(self, new_item, db_item):
        # TODO: switch to usage of application-wide utility method
        """
        Creates or updates a database item.
        """
        plr = Player.find_by_id(new_item.player_id)
        cls_name = new_item.HUMAN_READABLE

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
