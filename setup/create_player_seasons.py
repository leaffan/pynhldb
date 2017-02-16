#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import concurrent.futures

from db.common import session_scope
from db.player import Player
from db.team import Team
from utils.player_data_retriever import PlayerDataRetriever

logger = logging.getLogger(__name__)


def create_player_seasons():
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
                player.player_id
            ): player for player in players
        }
        for future in concurrent.futures.as_completed(future_tasks):
            try:
                plr_season_count += len(future.result())
            except Exception as e:
                print("Concurrent task generated an exception: %s" % e)

    logger.info("+ %d statistics items retrieved overall" % plr_season_count)


def create_player_data():
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
                player.player_id
            ): player for player in players
        }
        for future in concurrent.futures.as_completed(future_tasks):
            try:
                pass
            except Exception as e:
                print("Concurrent task generated an exception: %s" % e)


def create_player_contracts():
    """
    Creates player contract items in database.
    """
    data_retriever = PlayerDataRetriever()

    with session_scope() as session:
        players = session.query(Player).all()[:]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
        future_tasks = {
            threads.submit(
                data_retriever.retrieve_player_contracts,
                player.player_id
            ): player for player in players
        }
        for future in concurrent.futures.as_completed(future_tasks):
            try:
                pass
            except Exception as e:
                print("Concurrent task generated an exception: %s" % e)


def create_capfriendly_ids():
    """
    Creates capfriendly id attributes for players in database.
    """
    data_retriever = PlayerDataRetriever()

    with session_scope() as session:
        players = session.query(Player).all()[:]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
        future_tasks = {
            threads.submit(
                data_retriever.retrieve_capfriendly_id,
                player.player_id
            ): player for player in players
        }
        for future in concurrent.futures.as_completed(future_tasks):
            try:
                pass
            except Exception as e:
                print("Concurrent task generated an exception: %s" % e)


def create_capfriendly_ids_by_team():

    data_retriever = PlayerDataRetriever()

    from sqlalchemy import and_

    with session_scope() as session:
        teams = session.query(Team).filter(
            and_(
                Team.last_year_of_play.is_(None),
                Team.first_year_of_play < 2017
            )
        ).all()

    for team in sorted(teams)[:]:
        print(team)
        data_retriever.retrieve_capfriendly_ids(team.team_id)
