#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging
import json
from operator import sub, itemgetter

import requests
from lxml import html

logger = logging.getLogger(__name__)
BASE_HREF = "http://www.hockey-reference.com"
MORE_REGEX = re.compile("More\s(.+)\sPages")

ROSTER_SIZE_ADJUSTMENT = True
ROSTER_PER_SEASON = json.loads(
    open("analysis/rosters_per_season.json").read())


def retrieve_and_adjust_goal_totals(players_src, goals_per_season_src):
    """
    Retrieves and adjusts season goal scoring totals for specified players.
    """
    # loading data
    players_data = json.load(open(players_src))
    goals_per_season_data = json.load(open(goals_per_season_src))

    # TODO: automatically determine whether we're currently in mid-season
    if 'overall' in goals_per_season_data:
        del goals_per_season_data['overall']
    # last_full_season = sorted(
    #     [int(s.split("-")[0]) for s in goals_per_season_data.keys()]).pop()

    adjusted_data = list()

    for plr in sorted(players_data, key=itemgetter('url'))[:5]:
        plr_name = plr['name']
        plr_link = plr['url']
        # retrieving regular goal data from player stats page, thereby
        # optionally excluding the most recent season, usually an on-going one
        # TODO: see above
        full_name, regular_goal_data = retrieve_regular_goal_totals(
            plr_name, plr_link, exclude_most_recent_season=True)
        # full_name, regular_goal_data = retrieve_regular_goal_totals(
        #     plr_name, plr_link)
        # adjusting goal scoring totals per season
        adjusted_goal_data = calculate_adjusted_goals(
            regular_goal_data, goals_per_season_data)
        adjusted_goal_data['yearly_leader'] = plr['yearly_leader']

        adjusted_data.append(adjusted_goal_data)

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

        # calculating seasonally adjusted goal total
        adjusted_goals = round(
            goals_per_season_data[season]['adjustment_factor'] * goals, 4)
        if ROSTER_SIZE_ADJUSTMENT:
            # adjusting goal total by roster size
            adjusted_goals = round(
                ROSTER_PER_SEASON[season]['adjustment_factor'] *
                adjusted_goals, 4)

        goal_data['adjusted_goals'].append(adjusted_goals)
        # adding adjusted goal total for season to sum of adjusted goals
        sum_adjusted_goals += adjusted_goals

    goal_data['sum_adjusted_goals'] = round(sum_adjusted_goals, 4)
    goal_data['adjusted_goals_per_game'] = round(
            sum_adjusted_goals / sum(goal_data['games']), 4)
    goal_data['adjusted_goals_per_season'] = round(
            sum_adjusted_goals / sum(goal_data['games']) * 82, 4)
    goal_data['adjusted_goals_diff_game'] = sub(
        goal_data['adjusted_goals_per_game'], goal_data['goals_per_game'])
    goal_data['adjusted_goals_diff_season'] = sub(
        goal_data['adjusted_goals_per_season'], goal_data['goals_per_season'])

    logger.info("\t+ %d adjusted goals, %.4f adjusted goals per game" % (
        goal_data['sum_adjusted_goals'], goal_data['adjusted_goals_per_game']))

    return goal_data


def retrieve_regular_goal_totals(
        plr_name, plr_link, exclude_most_recent_season=False):
    """
    Retrieves regular season goal totals for specified player from player's
    stats page.
    """
    logger.info("+ Retrieving goal totals for %s " % plr_name)

    single_player_data = dict()

    url = "".join((BASE_HREF, plr_link))
    r = requests.get(url)
    doc = html.fromstring(r.text)

    full_name = doc.xpath("//h1/text()").pop(0)
    single_player_data['full_name'] = full_name
    single_player_data['url'] = url

    # separating full name into last and first name
    more_pages_text = doc.xpath(
        "//li[@data-fade-selector='#inpage_nav' and " +
        "@class='condensed hasmore ']/a/text()")
    if more_pages_text:
        more_pages_text = more_pages_text.pop(0)
        last_name = re.search(MORE_REGEX, more_pages_text).group(1)
        single_player_data['last_name'] = last_name
        single_player_data['first_name'] = full_name.replace(
            last_name, "").strip()
    else:
        (
            single_player_data['first_name'],
            single_player_data['last_name']
        ) = full_name.split()

    # retrieving table with standard player stats
    table = doc.xpath(
        "//table[@id='stats_basic_nhl' or @id='stats_basic_plus_nhl']/tbody")
    table = table.pop(0)

    # retrieving seasons played from standard player stats table
    # the following expression does not exclude WHA seasons
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
    # the following expression does not exclude WHA seasons
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
    # the following expression does not exclude WHA seasons
    # goals_scored = [int(x) for x in table.xpath(
    #     "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, " +
    #     "'stats_basic_plus_nhl.')]/td[@data-stat='goals']//text()")]
    # expression only considering NHL seasons:
    goals_scored = [int(x) for x in table.xpath(
        "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, " +
        "'stats_basic_plus_nhl.')]/td[@data-stat='lg_id']/a[text() = 'NHL']" +
        "/parent::*/following-sibling::td[@data-stat='goals']//text()"
    )]

    # excluding most recent season from data, this might be necessary if we're
    # currently in mid-season (for which one an adjustment factor has not
    # been provided yet)
    # TODO: dynamic way of finding current season
    if exclude_most_recent_season and seasons_played[-1] == "2018-19":
        seasons_played = seasons_played[:-1]
        games_played = games_played[:-1]
        goals_scored = goals_scored[:-1]

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

    return full_name, single_player_data


if __name__ == '__main__':

    players_src = r"nhl_goals_leaders.json"
    goals_per_season_src = r"nhl_games_per_season.json"

    adjusted_goal_data = retrieve_and_adjust_goal_totals(
        players_src, goals_per_season_src)
