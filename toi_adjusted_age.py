#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import math
import numpy as np
# import matplotlib.pyplot as plt

from datetime import timedelta
from operator import attrgetter

# from db.common import session_scope
from db.game import Game
from db.player_game import PlayerGame
from db.player_data_item import PlayerDataItem
from db.team import Team


def calculate_mean_age(
        season, game_id, plr_types='', toi_type='', query_team=''):
    # retrieving game
    game = Game.find_by_id(game_id)
    # retrieving players participating in game
    players_in_game = PlayerGame.get_players_in_game(game.game_id)
    # positions = ["L", "R", "C"])

    toi_type = "toi_ev"

    # differentiating between players for and home and away team
    for key in players_in_game.keys():
        team = Team.find_by_id(players_in_game[key]['team_id'])

        if team != query_team:
            continue

        plr_games = players_in_game[key]['player_games']
        # retrieving basic player data
        plr_infos = PlayerDataItem.find_by_player_ids(
            map(attrgetter('player_id'), plr_games))
        # retrieving age for each player
        plr_ages = dict()
        for plr_info in plr_infos:
            # print(
            #     "\t", plr_info.player_id,
            #     (game.date - plr_info.date_of_birth).days)
            plr_ages[plr_info.player_id] = (
                game.date - plr_info.date_of_birth).days
        # calculating standard mean age
        std_mean_age = np.mean(list(plr_ages.values()))
        # retrieving time on ice for each player
        plr_toi = dict()
        for plr_game in plr_games:
            plr_toi[plr_game.player_id] = getattr(plr_game, toi_type)
        # retrieving summarized time on ice for current team
        toi_overall = sum(
            [t.seconds for t in map(attrgetter(toi_type), plr_games)])
        toi_overall = timedelta(seconds=toi_overall)
        # calculating weighted mean age
        weighted_mean_age = 0
        for player_id in plr_ages:
            print(
                player_id, plr_ages[player_id], plr_toi[player_id],
                float(plr_toi[player_id].seconds) / toi_overall.seconds)
            weighted_mean_age += (
                plr_ages[player_id] *
                float(plr_toi[player_id].seconds) /
                toi_overall.seconds)

        std_mean_age = timedelta(days=int(std_mean_age))
        weighted_mean_age = timedelta(days=int(weighted_mean_age))

        print("Mean age: %d years %d days" % (
            std_mean_age.days / 365, std_mean_age.days % 365))
        print("Weighted mean age: %d years %d days" % (
            weighted_mean_age.days / 365, weighted_mean_age.days % 365))
        print("Difference: %+d days" % (
            weighted_mean_age.days - std_mean_age.days))

        return (std_mean_age, weighted_mean_age)


# def plot_stuff(std_mean_age, weighted_mean_age):

#     x = [v.days for v in std_mean_age]
#     y = [v.days for v in weighted_mean_age]

#     plt.scatter(x, y)


def process_team(season, team):
    games = Game.find_by_season_team(season, team)

    std_ages = list()
    weighted_ages = list()
    output = list()
    output.append("team,game_id,std_mean_age,weighted_mean_age")

    for g in games:
        print(g.game_id)
        std_age, weighted_age = calculate_mean_age(
            season, g.game_id, query_team=team)
        std_ages.append(std_age)
        weighted_ages.append(weighted_age)
        output.append(",".join((
            team.name, str(g.game_id), "%.4f" % (std_age.days / 365.),
            "%.4f" % (int(weighted_age.days) / 365.))))

    open(R"d:\%d_%s.csv" % (season, team.abbr), 'w').write("\n".join(output))

    # plot_stuff(std_ages, weighted_ages)


if __name__ == '__main__':

    season = 2016
    # game_id = "020001"

    # team = Team.find('TOR')
    # games = Game.find_by_season_team(season, team)

    for team in sorted(Team.find_teams_for_season(season))[:]:
        if not team.abbr == 'TOR':
            continue
        print(team)
        process_team(season, team)
    # process_team(season, "NJD")

    # plt.show()

    # for g in games:
    #     std_mean_age, weighted_mean_age = calculate_mean_age(
    #         season, g.nhl_id, query_team=team)
    #     x.append(std_mean_age.days)
    #     y.append(weighted_mean_age.days)
    #     # s.append(abs(weighted_mean_age.days - std_mean_age.days))

    # plot_stuff(x, y)
    # plot_stuff(a, b)

    # z = np.polyfit(x, y, 1)
    # p = np.poly1d(z)
    # plt.plot(x, p(x))
    # plt.plot(x, x)
    # # print "y=%.6fx+(%.6f)" %(z[0],z[1])

    # plt.show()
