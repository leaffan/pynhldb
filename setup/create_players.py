#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from concurrent.futures import ThreadPoolExecutor, as_completed

from db import commit_db_item
from db.player import Player
from db.team import Team
from utils.player_finder import PlayerFinder
from utils.player_data_retriever import PlayerDataRetriever
from utils.eliteprospects_utils import retrieve_drafted_players_with_dobs

MAX_WORKERS = 8


def migrate_players(plr_src_file=None):
    """
    Migrates players from specified JSON file to currently connected database.
    """
    if not plr_src_file:
        plr_src_file = os.path.join(
            os.path.dirname(__file__), 'nhl_players.json')

    migration_data = json.load(open(plr_src_file))

    for player_id in sorted(migration_data.keys())[:]:

        last_name = migration_data[player_id]['last_name']
        first_name = migration_data[player_id]['first_name']
        position = migration_data[player_id]['position']

        alternate_last_names = migration_data[player_id].get(
            'alternate_last_names', None)
        alternate_first_names = migration_data[player_id].get(
            'alternate_first_names', None)
        alternate_positions = migration_data[player_id].get(
            'alternate_positions', None)

        plr = Player(
            player_id, last_name, first_name, position,
            alternate_last_names=alternate_last_names,
            alternate_first_names=alternate_first_names,
            alternate_positions=alternate_positions
        )

        print("Working on %s" % plr)

        commit_db_item(plr)


def search_players(src_type, teams=None, season=None):
    """
    Searches (and optionally creates) players that are listed either on the
    each team's official roster page (source type 'roster') or on its *in-the-
    system* page (source type 'sytem'). Finally retrieves career regular season
    and playoff statistics for each player.
    """
    plr_f = PlayerFinder()
    plr_r = PlayerDataRetriever()
    if teams is None:
        if season is None:
            # using current teams (if nothing else is specfied)            
            teams_of_interest = Team.find_teams_for_season()
        else:
            # using teams from specified season
            teams_of_interest = Team.find_teams_for_season(season)
    else:
        # explicitly using specified teams
        teams_of_interest = Team.find_teams_with_abbrs(teams)

    for team in sorted(teams_of_interest)[:]:
        team_players = plr_f.find_players_for_team(team, src_type, season)

        # using concurrent threads to speed up the retrieval of single player
        # season statistics
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as threads:
            future_tasks = {
                threads.submit(
                    plr_r.retrieve_player_seasons,
                    plr.player_id): plr for plr in team_players}
            for future in as_completed(future_tasks):
                try:
                    # TODO: think of something to do with the result here
                    data = future.result()
                except Exception as e:
                    print
                    print("Conccurrent task generated an exception: %s" % e)


def create_players_for_draft_year(draft_year):
    """
    Uses specified draft year to create database items for each drafted player.
    """
    # retrieving suggestions from nhl.com for all retrieved drafted players
    suggested_plrs = get_suggestions_for_drafted_players(draft_year)

    for suggested_plr in suggested_plrs:
        # exploding tuple
        # TODO: use named tuple
        (
            plr_id, position, last_name,
            first_name, dob, alt_last_name
        ) = suggested_plr

        # checking if player already exists
        plr = Player.find_by_id(plr_id)

        # if yes, announcing a player item's existence
        if plr is not None:
            print("+ %s already existing in database" % plr)
        # otherwise creating it
        else:
            plr = Player(
                plr_id, last_name, first_name,
                position, alternate_last_names=alt_last_name)
            commit_db_item(plr)
            print("+ %s created" % Player.find_by_id(plr_id))


def get_suggestions_for_drafted_players(draft_year):
    """
    Retrieves player id suggestions from nhl.com for all players drafted in
    specified year.
    """
    # retrieving players (with date of births and alternate last names) drafted
    # in specified year
    drafted_players = retrieve_drafted_players_with_dobs(draft_year)

    print(
        "+ Basic information retrieved for " +
        "%d players drafted in %d" % (len(drafted_players), draft_year))

    pfr = PlayerFinder()
    suggested_players = list()

    for drafted_plr in drafted_players:
        # trying to find suggestions by using both first and last name
        suggestions = pfr.get_suggested_players(
            drafted_plr.last_name, drafted_plr.first_name)
        # otherwise trying to find suggestions for last name only
        if not suggestions:
            print(
                "+ No suggestion found " +
                "for %s %s. " % (
                    drafted_plr.first_name, drafted_plr.last_name) +
                "Trying last name only.")
            suggestions = pfr.get_suggested_players(drafted_plr.last_name)
        # otherwise trying to find suggestions for alternate
        # last name (if applicable)
        if not suggestions and drafted_plr.alt_last_name:
            print(
                "+ No suggestion found for %s. " % drafted_plr.last_name +
                "Trying alternate last names.")
            suggestions = pfr.get_suggested_players(drafted_plr.alt_last_name)

        if len(suggestions) > 1:
            print(
                "+ %d suggestions found " % len(suggestions) +
                "for %s %s" % (drafted_plr.first_name, drafted_plr.last_name))

        # finding out the exact suggestion by comparing dates of birth
        for suggestion in suggestions:
            suggested_dob = suggestion[-1]
            if suggested_dob == drafted_plr.date_of_birth:
                break
        else:
            print("+ No matching date of birth found for %s %s" % (
                drafted_plr.first_name, drafted_plr.last_name))
            continue

        if drafted_plr.alt_last_name:
            if suggestion[2] == drafted_plr.last_name:
                suggestion = suggestion + (drafted_plr.alt_last_name,)
            else:
                suggestion = suggestion + (drafted_plr.last_name,)
        else:
            suggestion = suggestion + ('',)

        suggested_players.append(suggestion)

    return suggested_players
