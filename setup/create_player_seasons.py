#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import concurrent.futures

from db.common import session_scope
from db.player import Player
from utils.player_data_retriever import PlayerDataRetriever

logger = logging.getLogger(__name__)


def create_player_seasons(simulation=False):

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
