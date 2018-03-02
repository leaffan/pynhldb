#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict
from operator import attrgetter

from sqlalchemy import cast, String, and_
from colorama import Fore, init, Style

from db.common import session_scope
from db.team import Team
from db.game import Game
from db.team_game import TeamGame


def determine_format_string(value):
        # determining color for goal differential output
    if value > 0:
        fore = Fore.LIGHTGREEN_EX
        diff_str = "+%2d" % value
    elif value < 0:
        fore = Fore.LIGHTRED_EX
        diff_str = "-%2d" % abs(value)
    else:
        fore = Fore.LIGHTYELLOW_EX
        diff_str = "%3d" % 0

    return fore, diff_str


if __name__ == '__main__':

    season = 2017

    with session_scope() as session:
        # retrieving all teams for specified season
        teams = session.query(Team).filter(and_(
            Team.first_year_of_play <= season,
            Team.last_year_of_play.is_(None)
        )).all()
        # retrieving games played by teams in specified season
        team_games = session.query(
            TeamGame).filter(cast(
                TeamGame.game_id, String).like("%d02%%" % season)).all()
        last_game_date = max(map(
            attrgetter('date'),
            session.query(Game).filter(Game.season == season).all()))

    team_goals_summary = dict()

    # aggregating goals for and goals against
    for tg in team_games:
        if tg.team_id not in team_goals_summary:
            team_goals_summary[tg.team_id] = defaultdict(int)

        team_goals_summary[tg.team_id]['gf_1'] += tg.goals_for_1st
        team_goals_summary[tg.team_id]['ga_1'] += tg.goals_against_1st
        team_goals_summary[tg.team_id]['gf_2'] += tg.goals_for_2nd
        team_goals_summary[tg.team_id]['ga_2'] += tg.goals_against_2nd
        team_goals_summary[tg.team_id]['gf_3'] += tg.goals_for_3rd
        team_goals_summary[tg.team_id]['ga_3'] += tg.goals_against_3rd
        team_goals_summary[tg.team_id]['gf'] += tg.goals_for
        team_goals_summary[tg.team_id]['ga'] += tg.goals_against

        # decreasing actual goals scored by one for an overtime win
        if tg.overtime_win:
            team_goals_summary[tg.team_id]['gf'] -= 1
        # decreasing actual goals allowed by one for an overtime loss
        if tg.overtime_loss:
            team_goals_summary[tg.team_id]['ga'] -= 1

    # calculating goal differences
    for team in teams:
        team_goals_summary[team.team_id]['gd_1'] = (
            team_goals_summary[team.team_id]['gf_1'] -
            team_goals_summary[team.team_id]['ga_1']
        )
        team_goals_summary[team.team_id]['gd_2'] = (
            team_goals_summary[team.team_id]['gf_2'] -
            team_goals_summary[team.team_id]['ga_2']
        )
        team_goals_summary[team.team_id]['gd_3'] = (
            team_goals_summary[team.team_id]['gf_3'] -
            team_goals_summary[team.team_id]['ga_3']
        )
        team_goals_summary[team.team_id]['gd'] = (
            team_goals_summary[team.team_id]['gf'] -
            team_goals_summary[team.team_id]['ga']
        )

    i = 1
    init()
    print()
    print(
        " + NHL Goal Differential per Period (%s)" % (
            last_game_date.strftime("%b %d, %Y")))
    print("  # %-22s %4s %4s %4s %4s %4s %4s %4s %4s %4s %4s %4s %4s" % (
        'Team', 'GF', 'GA', 'GD', 'GF1', 'GA1', 'GD1', 'GF2',
        'GA2', 'GD2', 'GF3', 'GA3', 'GD3'))

    # sorting teams by goal differential
    for team_id in sorted(team_goals_summary, key=lambda x: (
            team_goals_summary[x]['gd'],
            team_goals_summary[x]['gf']), reverse=True):
        team = Team.find_by_id(team_id)

        print(
            "%3d %-22s%5d%5d%s%5s%s" % (
                i, team,
                team_goals_summary[team_id]['gf'],
                team_goals_summary[team_id]['ga'],
                *determine_format_string(team_goals_summary[team_id]['gd']),
                Style.RESET_ALL) +
            "%5d%5d%s%5s%s" % (
                team_goals_summary[team_id]['gf_1'],
                team_goals_summary[team_id]['ga_1'],
                *determine_format_string(team_goals_summary[team_id]['gd_1']),
                Style.RESET_ALL) +
            "%5d%5d%s%5s%s" % (
                team_goals_summary[team_id]['gf_2'],
                team_goals_summary[team_id]['ga_2'],
                *determine_format_string(team_goals_summary[team_id]['gd_2']),
                Style.RESET_ALL) +
            "%5d%5d%s%5s%s" % (
                team_goals_summary[team_id]['gf_3'],
                team_goals_summary[team_id]['ga_3'],
                *determine_format_string(team_goals_summary[team_id]['gd_3']),
                Style.RESET_ALL)
        )
        i += 1
