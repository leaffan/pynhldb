#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from collections import defaultdict

import requests
from lxml import html

BASE_HREF = "http://www.hockey-reference.com"


players_src = r"nhl_goals_leaders.json"
goals_per_season_src = r"nhl_games_per_season.json"

players = json.load(open(players_src))
goals_per_season = json.load(open(goals_per_season_src))

adjusted_goals_per_player = defaultdict(dict)

for plr_link, plr_name in sorted(players)[:1]:
    print("+ Adjusting goal totals for %s " % plr_name)
    url = "".join((BASE_HREF, plr_link))
    r = requests.get(url)
    doc = html.fromstring(r.text)

    # retrieving table with standard player stats
    table = doc.xpath(
        "//table[@id='stats_basic_nhl' or @id='stats_basic_plus_nhl']/tbody")
    table = table.pop(0)

    # retrieving seasons played from standard player stats table
    seasons_played = table.xpath(
        "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, 'stats_basic_plus_nhl.')]/th[@data-stat='season']/text()")
    # retrieving games played in each season from standard player stats table
    games_played = [int(x) for x in table.xpath(
        "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, 'stats_basic_plus_nhl.')]/td[@data-stat='games_played']//text()")]
    # retrieving goals scored in each season from standard player stats table
    goals_scored = [int(x) for x in table.xpath(
        "tr[contains(@id, 'stats_basic_nhl.') or contains(@id, 'stats_basic_plus_nhl.')]/td[@data-stat='goals']//text()")]

    # checking whether number of retrieved data items matches
    assert len(seasons_played) == len(goals_scored)
    assert len(seasons_played) == len(games_played)

    adjusted_goals_per_player[plr_name]['goals'] = goals_scored
    adjusted_goals_per_player[plr_name]['sum_goals'] = sum(goals_scored)
    adjusted_goals_per_player[plr_name]['games'] = games_played
    adjusted_goals_per_player[plr_name]['sum_games'] = sum(games_played)
    adjusted_goals_per_player[plr_name]['goals_per_game'] = round(
        sum(goals_scored) / sum(games_played), 4)
    adjusted_goals_per_player[plr_name]['goals_per_season'] = round(
        sum(goals_scored) / sum(games_played) * 82, 4)
    adjusted_goals_per_player[plr_name]['seasons'] = seasons_played
    adjusted_goals_per_player[plr_name]['sum_seasons'] = len(seasons_played)

    adjusted_goals_per_player[plr_name]['adjusted_goals'] = list()
    sum_adjusted_goals = 0

    # adjusting goals scored by adjustment factor for each season
    for season, goals in zip(seasons_played, goals_scored):

        if season not in goals_per_season:
            continue

        # calculating season-adjusted goal total
        adjusted_goals = round(
            goals_per_season[season]['adjustment_factor'] * goals, 4)
        adjusted_goals_per_player[plr_name]['adjusted_goals'].append(
            adjusted_goals)
        # adding adjusted goal total for season to sum of adjusted goals
        sum_adjusted_goals += adjusted_goals

        print(season, goals, adjusted_goals)

    adjusted_goals_per_player[plr_name][
        'sum_adjusted_goals'] = sum_adjusted_goals
    adjusted_goals_per_player[plr_name][
        'adjusted_goals_per_game'] = round(
            sum_adjusted_goals / sum(games_played), 4)
    adjusted_goals_per_player[plr_name][
        'adjusted_goals_per_season'] = round(
            sum_adjusted_goals / sum(games_played) * 82, 4)

# open(r"nhl_goals_adjusted.json", 'w').write(
#     json.dumps(adjusted_goals_per_player, sort_keys=True, indent=2))
