#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import concurrent.futures

from db.common import session_scope
from db.player import Player
from utils.player_data_retriever import PlayerDataRetriever

logger = logging.getLogger(__name__)


def create_player_seasons(simulation=False):
    """
    Creates player season database objects.
    """
    data_retriever = PlayerDataRetriever()
    plr_season_count = 0

    with session_scope() as session:
        players = session.query(Player).all()[:]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
            future_tasks = {
                threads.submit(
                    data_retriever.retrieve_player_seasons,
                    player.player_id, simulation
                ): player for player in players
            }
            for future in concurrent.futures.as_completed(future_tasks):
                try:
                    plr_season_count += len(future.result())
                except Exception as e:
                    print("Concurrent task generated an exception: %s" % e)

    logger.info("+ %d statistics items retrieved overall" % plr_season_count)


def create_player_data(simulation=False):
    """
    Creates player data items in database.
    """
    data_retriever = PlayerDataRetriever()

    with session_scope() as session:
        players = session.query(Player).all()[:]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
            future_tasks = {
                threads.submit(
                    data_retriever.retrieve_player_data,
                    player.player_id, simulation
                ): player for player in players
            }
            for future in concurrent.futures.as_completed(future_tasks):
                try:
                    pass
                except Exception as e:
                    print("Concurrent task generated an exception: %s" % e)


def create_player_contracts(simulation=False):
    """
    Creates player contract items in database.
    """
    data_retriever = PlayerDataRetriever()

    player_ids = [8467329, 8470595, 8477939, 8467950, 8462042, 8467496]

    for player_id in player_ids:
        data_retriever.retrieve_raw_contract_data(player_id)

    #     with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
    #         future_tasks = {
    #             threads.submit(
    #                 data_retriever.retrieve_player_data,
    #                 player.player_id, simulation
    #             ): player for player in players
    #         }
    #         for future in concurrent.futures.as_completed(future_tasks):
    #             try:
    #                 pass
    #             except Exception as e:
    #                 print("Concurrent task generated an exception: %s" % e)
