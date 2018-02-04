#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from operator import attrgetter

from sqlalchemy import and_, String, cast

from db.common import session_scope
from db.player import Player
from db.team import Team
from db.player_game import PlayerGame
from db.player_season import PlayerSeason

# TODO: command line arguments, comparison of all applicable stat values
season = 2016
season_type = 'RS'
stat_criterion = 'assists'

PS_PG_MAPPING = {
    'shots': 'shots_on_goal',
    'shifts': 'no_shifts',
    'toi': 'toi_overall'
}

if __name__ == '__main__':

    # retrieving arguments specified on command line
    parser = argparse.ArgumentParser(
        description='Download NHL game summary reports.')
    parser.add_argument(
        '-s', '--season', dest='season', required=False,
        metavar='season to check stats for',
        help="Season for which stats data will be checked")
    parser.add_argument(
        '-t', '--type', dest='season_type', required=False,
        metavar='season type', choices=['RS', 'PO'],
        help="Season type, e.g. regular season (RS) or playoffs (PO)")
    parser.add_argument(
        '-c', '--criterion', dest='stat_criterion', required=False,
        choices=[
            'goals', 'assists', 'points', 'pim', 'plus_minus', 'shots',
            'hits', 'blocks', 'shifts', 'toi'
        ],
        metavar='statistics criterion to be checked',
        help="Statistics criterion to be checked")

    args = parser.parse_args()

    if args.season is not None:
        season = int(args.season)
    else:
        season = 2017

    if args.stat_criterion is not None:
        stat_criterion = args.stat_criterion
    else:
        stat_criterion = 'goals'

    if args.season_type is not None:
        season_type = args.season_type
    else:
        season_type = 'RS'

    with session_scope() as session:

        # retrieving player seasons for specified season and season type
        pseasons = session.query(PlayerSeason).filter(
            and_(
                PlayerSeason.season == season,
                PlayerSeason.season_type == season_type
            )
        ).all()

        print("+ %d individual season statlines retrieved" % len(pseasons))

        for pseason in sorted(pseasons)[:]:

            plr = Player.find_by_id(pseason.player_id)
            # retrieving individual player games for specified player
            # TODO: group by team, i.e. for players with multiple stints with
            # a team in one season
            pgames = session.query(PlayerGame).filter(
                and_(
                    PlayerGame.player_id == pseason.player_id,
                    cast(PlayerGame.game_id, String).like("%d02%%" % season),
                    PlayerGame.team_id == pseason.team_id
                )
            ).all()

            if stat_criterion in PS_PG_MAPPING:
                stats_value = sum(
                    map(attrgetter(PS_PG_MAPPING[stat_criterion]), pgames))
            else:
                stats_value = sum(map(attrgetter(stat_criterion), pgames))
            team = Team.find_by_id(pseason.team_id)

            # print(plr, stats_value, getattr(pseason, stat_criterion))

            try:
                assert stats_value == getattr(pseason, stat_criterion)
            except Exception as e:
                print(plr)
                print("\t %s in player games for %s: %d" % (
                    stat_criterion.capitalize(), team, stats_value))
                print("\t %s in player season stats for %s: %d" % (
                    stat_criterion.capitalize(), team,
                    getattr(pseason, stat_criterion)))
