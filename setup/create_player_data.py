#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import concurrent.futures
from datetime import date

from sqlalchemy import and_

from db.common import session_scope
from db.player import Player
from db.team import Team
from utils.player_finder import PlayerFinder
from utils.player_data_retriever import PlayerDataRetriever
from utils.player_contract_retriever import PlayerContractRetriever
from utils.player_draft_retriever import PlayerDraftRetriever
from utils.capfriendly_utils import retrieve_capfriendly_ids
from utils.capfriendly_utils import retrieve_capfriendly_id
from utils.capfriendly_utils import retrieve_latest_signings


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
            ): player for player in sorted(players)
        }
        for future in concurrent.futures.as_completed(future_tasks):
            try:
                pass
            except Exception as e:
                print("Concurrent task generated an exception: %s" % e)


def create_player_contracts(player_ids=None):
    """
    Creates player contract items in database.
    """
    data_retriever = PlayerContractRetriever()

    with session_scope() as session:
        players = sorted(session.query(Player).all())[:]

    if player_ids:
        players = list(filter(lambda p: p.player_id in player_ids, players))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
        future_tasks = {
            threads.submit(
                data_retriever.retrieve_player_contracts,
                player.player_id
            ): player for player in sorted(players)[:]
        }
        for future in concurrent.futures.as_completed(future_tasks):
            try:
                pass
            except Exception as e:
                print("Concurrent task generated an exception: %s" % e)


def create_player_contracts_by_team(teams=None):
    """
    Creates player contract items in database on a per-team basis.
    """
    with session_scope() as session:
        if teams is None:
            teams_of_interest = session.query(Team).filter(
                and_(
                    Team.last_year_of_play.is_(None),
                    Team.first_year_of_play <= date.today().year
                )
            ).all()
        else:
            # explicitly using specified teams
            teams_of_interest = Team.find_teams_with_abbrs(teams)

    data_retriever = PlayerContractRetriever()
    player_finder = PlayerFinder()

    for team in sorted(teams_of_interest)[:]:
        print(
            "+ Retrieving contracts for players affiliated with the %s" % team)
        players = player_finder.get_contracted_players(team)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
            future_tasks = {
                threads.submit(
                    data_retriever.retrieve_player_contracts, player.player_id
                ): player for player in sorted(players)[:]
            }
            for future in concurrent.futures.as_completed(future_tasks):
                try:
                    pass
                except Exception as e:
                    print("Concurrent task generated an exception: %s" % e)


def create_player_drafts():
    """
    Creates player draft information for all players in database.
    """
    data_retriever = PlayerDraftRetriever()

    with session_scope() as session:
        players = session.query(Player).all()[:]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
        future_tasks = {
            threads.submit(
                data_retriever.retrieve_draft_information,
                player.player_id
            ): player for player in sorted(players)[:]
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
    with session_scope() as session:
        players = session.query(Player).all()[:]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
        future_tasks = {
            threads.submit(
                retrieve_capfriendly_id, player.player_id
            ): player for player in sorted(players)
        }
        for future in concurrent.futures.as_completed(future_tasks):
            try:
                pass
            except Exception as e:
                print("Concurrent task generated an exception: %s" % e)


def create_capfriendly_ids_by_team():
    """
    Creates capfriendly id attributes for all players of each team in database.
    """
    with session_scope() as session:
        teams = session.query(Team).filter(
            and_(
                Team.last_year_of_play.is_(None),
                Team.first_year_of_play <= date.today().year
            )
        ).all()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as threads:
        future_tasks = {
            threads.submit(
                retrieve_capfriendly_ids, team.team_id
            ): team for team in sorted(teams)[:]
        }
        for future in concurrent.futures.as_completed(future_tasks):
            try:
                pass
            except Exception as e:
                print("Concurrent task generated an exception: %s" % e)


def create_latest_contract_signings(max_existing_contracts_found=5):
    """
    Retrieves latest contract signings from capfriendly id and creates
    according data items in the database.
    """
    retrieve_latest_signings(max_existing_contracts_found)
