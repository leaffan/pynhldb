#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from collections import defaultdict

import requests
from lxml import html


URL_TEMPLATE = "http://www.hockey-reference.com/leagues/NHL_%d.html"

overall_sum_games_played = 0
overall_sum_goals_scored = 0

games_goals_per_year = defaultdict(dict)
goal_leaders = set()

for year in range(1918, 2017)[:10]:

    # skipping season completely lost to a lockout
    if year == 2005:
        continue

    season = "%d-%s" % (year - 1, str(year)[-2:])

    # retrieving raw html data and parsing it
    url = URL_TEMPLATE % year
    r = requests.get(url)
    doc = html.fromstring(r.text)

    # the stuff we're interested in is hidden in comments
    comments = doc.xpath("//comment()")

    for comment in comments:
        # removing comment markup
        sub = html.fromstring(str(comment)[3:-3])
        if not sub.xpath("//table/caption/text()"):
            continue
        if sub.xpath("//table/caption/text()")[0] == "Team Statistics Table":
                team_stats = sub

    # TODO: determine number of shootout wins to subtract that number
    # from team goal totals

    # retrieving games played by each team as list
    season_games_played = [
        int(x) for x in team_stats.xpath(
            "//tbody/tr/td[@data-stat='games']/text()")]
    # retrieving goals scored by each team as list
    season_goals_scored = [
        int(x) for x in team_stats.xpath(
            "//tbody/tr/td[@data-stat='goals']/text()")]

    assert len(season_games_played) == len(season_goals_scored)

    # summing up games played in current season
    season_games_played = int(sum(season_games_played) / 2)
    overall_sum_games_played += season_games_played
    # summing up goals scored in current season
    season_goals_scored = sum(season_goals_scored)
    overall_sum_goals_scored += season_goals_scored

    # adding per year data to result dictionary
    games_goals_per_year[year]['season'] = season
    games_goals_per_year[year]['games'] = season_games_played
    games_goals_per_year[year]['goals'] = season_goals_scored
    games_goals_per_year[year]['goals_per_game'] = round(
        season_goals_scored / season_games_played, 2)

    print("%s: %d games played, %d goals scored, %0.2f goals per game" % (
        season, season_games_played, season_goals_scored,
        round(season_goals_scored / season_games_played, 2)))

# calculating overall goals per game ratio
overall_goals_per_game = round(
    overall_sum_goals_scored / overall_sum_games_played, 2)

print(
    overall_sum_games_played, overall_sum_goals_scored,
    round(overall_sum_goals_scored / overall_sum_games_played, 2))

# calculating adjustment factor for each registered season
for year in sorted(games_goals_per_year.keys()):
    games_goals_per_year[
        year]['adjustment_factor'] = round((
            overall_goals_per_game / (
                games_goals_per_year[year]['goals_per_game'])), 4)
    print(games_goals_per_year[year]['season'])
    print(games_goals_per_year[year]['adjustment_factor'])

open(r"d:\nhl_games_per_season.json", 'w').write(
    json.dumps(games_goals_per_year, sort_keys=True, indent=2))
