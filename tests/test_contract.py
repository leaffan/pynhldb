#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.contract import Contract
from db.contract_year import ContractYear
from db.buyout import Buyout
from db.buyout_year import BuyoutYear
from utils.player_contract_retriever import PlayerContractRetriever


def test_contract_creation():

    player_id = 8467329  # Vincent Lecavalier

    pcr = PlayerContractRetriever()
    plr_contract_list = pcr.retrieve_raw_contract_data(player_id)

    assert len(plr_contract_list) == 3

    for plr_contract_dict in plr_contract_list:
        contract = Contract(player_id, plr_contract_dict)
        contract_db = Contract.find(
            player_id,
            plr_contract_dict['start_season'],
            plr_contract_dict['end_season'])

        assert contract == contract_db


def test_contract_year_creation():

    player_id = 8471675  # Sidney Crosby

    pcr = PlayerContractRetriever()
    plr_contract_list = pcr.retrieve_raw_contract_data(player_id)

    for plr_contract_dict in plr_contract_list:
        contract_db = Contract.find(
            player_id,
            plr_contract_dict['start_season'],
            plr_contract_dict['end_season'])

        for contract_year_dict in plr_contract_dict['contract_years']:
            contract_year = ContractYear(
                player_id, contract_db.contract_id, contract_year_dict)
            contract_year_db = ContractYear.find(
                player_id, contract_db.contract_id,
                contract_year_dict['season'])

            assert contract_year == contract_year_db


def test_buyout_creation():

    player_id = 8471362  # Mikhail Grabovski

    pcr = PlayerContractRetriever()
    plr_contract_list = pcr.retrieve_raw_contract_data(player_id)

    for plr_contract_dict in plr_contract_list:
        contract_db = Contract.find(
            player_id,
            plr_contract_dict['start_season'],
            plr_contract_dict['end_season'])

        if contract_db.bought_out:
            buyout_dict = pcr.retrieve_raw_buyout_data(player_id)
            buyout = Buyout(player_id, contract_db.contract_id, buyout_dict)
            buyout_db = Buyout.find(contract_db.contract_id)

            assert buyout == buyout_db


def test_buyout_year_creation():

    player_id = 8469555  # Christian Ehrhoff

    pcr = PlayerContractRetriever()
    plr_contract_list = pcr.retrieve_raw_contract_data(player_id)

    for plr_contract_dict in plr_contract_list:
        contract_db = Contract.find(
            player_id,
            plr_contract_dict['start_season'],
            plr_contract_dict['end_season'])

        if contract_db.bought_out:
            buyout_dict = pcr.retrieve_raw_buyout_data(player_id)
            buyout_db = Buyout.find(contract_db.contract_id)

            for buyout_year_data_dict in buyout_dict['buyout_years']:
                buyout_year = BuyoutYear(
                    player_id, buyout_db.buyout_id, buyout_year_data_dict)
                buyout_year_db = BuyoutYear.find(
                    buyout_db.buyout_id, buyout_year_data_dict['season'])

                assert buyout_year == buyout_year_db
