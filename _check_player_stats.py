#!/usr/bin/env python
# -*- coding: utf-8 -*-

from operator import attrgetter

from sqlalchemy import and_, String, cast

from db.common import session_scope
from db.player import Player
from db.player_game import PlayerGame
from db.player_season import PlayerSeason

# TODO: command line arguments, comparison of all applicable stat values
season = 2016
season_type = 'RS'
stat_criterion = 'goals'

if __name__ == '__main__':

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
            pgames = session.query(PlayerGame).filter(
                and_(
                    PlayerGame.player_id == pseason.player_id,
                    cast(PlayerGame.game_id, String).like("%d02%%" % season),
                    PlayerGame.team_id == pseason.team_id
                )
            ).all()


            stats_value = sum(map(attrgetter(stat_criterion), pgames))

            # print(plr, stats_value, getattr(pseason, stat_criterion))

            try:
                assert stats_value == getattr(pseason, stat_criterion)
            except Exception as e:
                print(plr)
                print("\t Goals in player games: %d" % stats_value)
                print("\t Goals in player season stats: %d" % pseason.goals)
