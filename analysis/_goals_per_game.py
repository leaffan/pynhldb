#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import json
from collections import defaultdict

import requests
from lxml import html

logger = logging.getLogger(__name__)
URL_TEMPLATE = "http://www.hockey-reference.com/leagues/NHL_%d.html"


def retrieve_goals_per_season(start_season=1917, end_season=2016):
    """
    Retrieves goals scored for each NHL season.
    """
    logger.info(
        "+ Calculating goals per game for all NHL " +
        "seasons between %d-%s and %d-%s" % (
            start_season, str(start_season + 1)[-2:],
            end_season, str(end_season + 1)[-2:]))
    season_data = defaultdict(dict)

    for year in range(start_season, end_season + 1)[:]:
        # skipping season completely lost to a lockout
        if year == 2004:
            continue

        # setting up season identifier
        season = "%d-%s" % (year, str(year + 1)[-2:])

        # retrieving raw html data and parsing it
        url = URL_TEMPLATE % (year + 1)
        r = requests.get(url)
        doc = html.fromstring(r.text)

        # the stuff we're interested in is hidden in comments
        comments = doc.xpath("//comment()")

        for comment in comments:
            # removing comment markup
            sub = html.fromstring(str(comment)[3:-3])
            if not sub.xpath("//table/caption/text()"):
                continue
            if sub.xpath(
                    "//table/caption/text()")[0] == "Team Statistics Table":
                        team_stats = sub

        # retrieving games played by each team as list
        season_games_played = [
            int(x) for x in team_stats.xpath(
                "//tbody/tr/td[@data-stat='games']/text()")]
        # retrieving shootout wins for each team as list
        season_shootout_wins = [
            int(x) for x in team_stats.xpath(
                "//tbody/tr/td[@data-stat='wins_shootout']/text()")]
        # retrieving goals scored by each team as list
        season_goals_scored = [
            int(x) for x in team_stats.xpath(
                "//tbody/tr/td[@data-stat='goals']/text()")]

        assert len(season_games_played) == len(season_goals_scored)
        if season_shootout_wins:
            assert len(season_goals_scored) == len(season_shootout_wins)

        # summing up games played in current season
        season_games_played = int(sum(season_games_played) / 2)
        # summing up shootout wins in current season
        season_shootout_wins = sum(season_shootout_wins)
        # summing up goals scored in current season
        # subtracting number of shootout wins as winning goals in those
        # aren't official goals
        season_goals_scored = sum(season_goals_scored) - season_shootout_wins

        # adding per year data to result dictionary
        season_data[season]['year'] = year
        season_data[season]['games'] = season_games_played
        season_data[season]['goals'] = season_goals_scored
        season_data[season]['goals_per_game'] = round(
            float(season_goals_scored) / season_games_played, 2)

        logger.info(
            "\t+ %s: %d games played, " % (season, season_games_played) +
            "%d goals scored, " % season_goals_scored +
            "%0.2f goals per game" % season_data[season]['goals_per_game'])

    return season_data


def calculate_adjustment_factors(season_data):
    """
    Calculates goal scoring adjustment factor for each season.
    """
    # retrieving number of goals scored in all seasons
    sum_goals_scored = sum(
        [season_data[season]['goals'] for season in season_data])
    # retrieving number of games played in all seasons
    sum_games_played = sum(
        [season_data[season]['games'] for season in season_data])

    # calculating overall goals per game ratio
    goals_per_game = round(
        float(sum_goals_scored) / sum_games_played, 2)

    logger.info(
        "\t+ Overall: %d games played, " % sum_games_played +
        "%d goals scored, " % sum_goals_scored +
        "%0.2f goals per game" % goals_per_game)
    logger.info("+ Calculating adjustment factors for each NHL season")

    # calculating adjustment factor for each registered season
    for season in sorted(season_data.keys()):
        season_data[season]['adjustment_factor'] = round(
            (goals_per_game / (season_data[season]['goals_per_game'])), 4)
        logger.info("\t+ %s: adjustment factor: %.4f" % (
            season, season_data[season]['adjustment_factor']))

    # adding overall values to result dictionary
    season_data['overall']['games'] = sum_games_played
    season_data['overall']['goals'] = sum_goals_scored
    season_data['overall']['goals_per_game'] = goals_per_game


if __name__ == '__main__':

    season_data = retrieve_goals_per_season()
    calculate_adjustment_factors(season_data)

    open(r"goals_per_season.json", 'w').write(
        json.dumps(season_data, sort_keys=True, indent=2))
