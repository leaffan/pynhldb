#!/usr/bin/env python
# -*- coding: utf-8 -*-

import concurrent.futures

from db.common import session_scope
from db.player import Player
from utils.player_data_retriever import PlayerDataRetriever


def create_player_seasons(simulation=False):

    data_retriever = PlayerDataRetriever()

    with session_scope() as session:

        players = session.query(Player).all()[:25]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
            future_tasks = {
                threads.submit(
                    data_retriever.retrieve_player_seasons,
                    player.player_id, simulation
                ): player for player in players
            }
            for future in concurrent.futures.as_completed(future_tasks):
                try:
                    plr_seasons = future.result()
                    print(len(plr_seasons))
                except Exception as e:
                    print("Concurrent task generated an exception: %s" % e)

