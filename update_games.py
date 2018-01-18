#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import date

from sqlalchemy import and_

from db.common import session_scope
from db.game import Game
from parsers.main_parser import MainParser

base_dir = R"D:\nhl\official_and_json"


if __name__ == '__main__':

    # retrieving games to be updated
    with session_scope() as session:
        games = session.query(Game).filter(
            and_(
                Game.home_team_id.in_([8, 9]),
                Game.date >= date(2011, 10, 11),
                Game.date <= date(2014, 4, 12)
            )
        ).all()

    # updating games by re-parsing corresponding summaries
    for game in sorted(games)[:]:

        season = str(game.game_id)[:4]
        season = "%d-%d" % (int(season), int(season) + 1 - 2000)
        game_id = str(game.game_id)[4:]

        src_dir = os.path.join(base_dir, season)
        src_month = str(game.date)[:7]
        src_path = os.path.join(src_dir, src_month, str(game.date) + ".zip")

        print(src_path, game_id)

        mp = MainParser(src_path, [game_id])
        mp.parse_games_sequentially(['events', 'shifts'])
