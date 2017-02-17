#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import json
from collections import defaultdict

import requests
from lxml import html

logger = logging.getLogger(__name__)
BASE_HREF = "http://www.hockey-reference.com"


def retrieve_and_adjust_goal_totals(players_src, goals_per_season_src):
    """
    Retrieves and adjusts season goal scoring totals for specified players.
    """
    # loading data
    players_data = json.load(open(players_src))
    goals_per_season_data = json.load(open(goals_per_season_src))

    adjusted_data = defaultdict(dict)

    for plr_link, plr_name in sorted(players_data)[:]:
        # retrieving regular goal data from player stats page
        regular_goal_data = retrieve_regular_goal_totals(plr_name, plr_link)
        # adjusting goal scoring totals per season
        adjusted_goal_data = calculate_adjusted_goals(
            regular_goal_data, goals_per_season_data)

        adjusted_data[plr_name] = adjusted_goal_data

    return adjusted_data


def calculate_adjusted_goals(goal_data, goals_per_season_data):
    """
    Calculates adjusted goals using per-season adjustment factors.
    """
    goal_data['adjusted_goals'] = list()
    sum_adjusted_goals = 0

    # logger.info(
    #     "+ Adjusting goal-scoring totals according to goals per season")

    # adjusting goals scored by adjustment factor for each season
    for season, goals in zip(goal_data['seasons'], goal_data['goals']):

        # skippings season for which no adjustment factor is available
        if season not in goals_per_season_data:
            continue

        # calculating season-adjusted goal total
        adjusted_goals = round(
            goals_per_season_data[season]['adjustment_factor'] * goals, 4)
        goal_data['adjusted_goals'].append(adjusted_goals)
        # adding adjusted goal total for season to sum of adjusted goals
        sum_adjusted_goals += adjusted_goals

    goal_data['sum_adjusted_goals'] = round(sum_adjusted_goals, 4)
    goal_data['adjusted_goals_per_game'] = round(
            sum_adjusted_goals / sum(goal_data['games']), 4)
    goal_data['adjusted_goals_per_season'] = round(
            sum_adjusted_goals / sum(goal_data['games']) * 82, 4)

    logger.info("\t+ %d adjusted goals, %.4f adjusted goals per game" % (
        goal_data['sum_adjusted_goals'], goal_data['adjusted_goals_per_game']))

    return goal_data


def retrieve_regular_goal_totals(plr_name, plr_link):
    """
    Retrieves regular season goal totals for specified player from player's
    stats page.
    """
    logger.info("+ Retrieving goal totals for %s " % plr_name)

    single_player_data = dict()

    url = "".join((BASE_HREF, plr_link))
    r = requests.get(url)
    doc = html.fromstring(r.text)

    # retrieving table with standard player stats
    table = doc.xpath(
        "//table[@id='stats_basic_nhl' or @id='stats_basic_plus_nhl']/tbody")
    table = table.pop(0)

    # retrieving seasons played from standard player stats table
    # the following expression does not include WHA seasons
    # seasons_played = table.xpath(
    #     "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, " +
    #     "'stats_basic_plus_nhl.')]/th[@data-stat='season']/text()")
    # expression only considering NHL seasons:
    seasons_played = table.xpath(
        "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, " +
        "'stats_basic_plus_nhl.')]/td[@data-stat='lg_id']/a[text() = 'NHL']" +
        "/parent::*/preceding-sibling::th/text()"
    )
    # retrieving games played in each season from standard player stats table
    # the following expression does not include WHA seasons
    # games_played = [int(x) for x in table.xpath(
    #     "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, " +
    #     "'stats_basic_plus_nhl.')]/td[@data-stat='games_played']//text()")]
    # expression only considering NHL seasons:
    games_played = [int(x) for x in table.xpath(
        "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, " +
        "'stats_basic_plus_nhl.')]/td[@data-stat='lg_id']/a[text() = 'NHL']" +
        "/parent::*/following-sibling::td[@data-stat='games_played']//text()"
    )]
    # retrieving goals scored in each season from standard player stats table
    # the following expression does not include WHA seasons
    # goals_scored = [int(x) for x in table.xpath(
    #     "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, " +
    #     "'stats_basic_plus_nhl.')]/td[@data-stat='goals']//text()")]
    # expression only considering NHL seasons:
    goals_scored = [int(x) for x in table.xpath(
        "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, " +
        "'stats_basic_plus_nhl.')]/td[@data-stat='lg_id']/a[text() = 'NHL']" +
        "/parent::*/following-sibling::td[@data-stat='goals']//text()"
    )]

    # checking whether number of retrieved data items matches
    assert len(seasons_played) == len(goals_scored)
    assert len(seasons_played) == len(games_played)

    single_player_data['goals'] = goals_scored
    single_player_data['sum_goals'] = sum(goals_scored)
    single_player_data['games'] = games_played
    single_player_data['sum_games'] = sum(games_played)
    single_player_data['goals_per_game'] = round(
        float(sum(goals_scored)) / sum(games_played), 4)
    single_player_data['goals_per_season'] = round(
        float(sum(goals_scored)) / sum(games_played) * 82, 4)
    single_player_data['seasons'] = seasons_played
    single_player_data['sum_seasons'] = len(seasons_played)

    logger.info("\t+ %d games played, %d goals scored, %.4f goals per game" % (
        sum(games_played), sum(goals_scored),
        single_player_data['goals_per_game']))

    return single_player_data


if __name__ == '__main__':

    players_src = r"nhl_goals_leaders.json"
    goals_per_season_src = r"nhl_games_per_season.json"

    adjusted_goal_data = retrieve_and_adjust_goal_totals(
        players_src, goals_per_season_src)
