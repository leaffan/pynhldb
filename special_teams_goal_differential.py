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
from db.event import Event
from db.goal import Goal

season = 2018


with session_scope() as session:
    # retrieving power play goals for specified season
    pp_goals = session.query(Goal, Event, Game).filter(and_(
        cast(Goal.event_id, String).like("%d02%%" % season),
        Event.event_id == Goal.event_id,
        Event.game_id == Game.game_id,
        Game.season == season,
        Event.num_situation == 'PP')).all()
    # retrieving shorthanded goals for specified season
    sh_goals = session.query(Goal, Event, Game).filter(and_(
        cast(Goal.event_id, String).like("%d02%%" % season),
        Event.event_id == Goal.event_id,
        Event.game_id == Game.game_id,
        Game.season == season,
        Event.num_situation == 'SH')).all()
    # retrieving teams for specified season
    # TODO: adjust query for others than the current season
    teams = session.query(Team).filter(and_(
        Team.first_year_of_play <= season,
        Team.last_year_of_play.is_(None)
    )).all()
    team_games = session.query(
        TeamGame).filter(cast(
            TeamGame.game_id, String).like("%d02%%" % season)).all()
    last_game_date = max(map(
        attrgetter('date'),
        session.query(Game).filter(Game.season == season).all()))

special_teams_summary = dict()

for goal, event, game in pp_goals[:]:
    if goal.team_id not in special_teams_summary:
        special_teams_summary[goal.team_id] = defaultdict(int)
    if goal.goal_against_team_id not in special_teams_summary:
        special_teams_summary[goal.goal_against_team_id] = defaultdict(int)

    # registering power play goals in special team summary
    special_teams_summary[goal.team_id]['ppgf'] += 1
    special_teams_summary[goal.goal_against_team_id]['ppga'] += 1

for goal, event, game in sh_goals[:]:
    if goal.team_id not in special_teams_summary:
        special_teams_summary[goal.team_id] = defaultdict(int)
    if goal.goal_against_team_id not in special_teams_summary:
        special_teams_summary[goal.goal_against_team_id] = defaultdict(int)

    # registering shorthanded goals in special teams summary
    special_teams_summary[goal.team_id]['shgf'] += 1
    special_teams_summary[goal.goal_against_team_id]['shga'] += 1

# calculating goal special teams goal differential
for team in teams:
    if team.team_id not in special_teams_summary:
        special_teams_summary[team.team_id] = defaultdict(int)
    special_teams_summary[team.team_id]['special_teams_diff'] = (
        special_teams_summary[team.team_id]['ppgf'] -
        special_teams_summary[team.team_id]['ppga'] +
        special_teams_summary[team.team_id]['shgf'] -
        special_teams_summary[team.team_id]['shga'])

for tg in team_games:
    special_teams_summary[tg.team_id]['pp_opps'] += tg.pp_overall
    special_teams_summary[tg.team_against_id]['tsh'] += tg.pp_overall


i = 1
init()
print()
print(
    " + NHL Special Teams Goal Differential & Combined Percentage (%s)" % (
        last_game_date.strftime("%b %d, %Y")))

print("  # %-22s %4s %4s %4s %4s %4s %4s %4s %4s %5s %4s" % (
    'Team', 'PPGF', 'SHGF', 'PPGA', 'SHGA',
    'PPO', 'PP%', 'TSH', 'PK%', 'PP+PK', 'STGD'))

# sorting teams by goal differential
for team_id in sorted(special_teams_summary, key=lambda x: (
        special_teams_summary[x]['special_teams_diff'],
        special_teams_summary[x]['ppgf'],
        special_teams_summary[x]['shgf']), reverse=True):
    team = Team.find_by_id(team_id)

    # determining color for goal differential output
    if special_teams_summary[team_id]['special_teams_diff'] > 0:
        diff_str = "+%2d" % special_teams_summary[
            team_id]['special_teams_diff']
        fore = Fore.LIGHTGREEN_EX
    elif special_teams_summary[team_id]['special_teams_diff'] < 0:
        diff_str = "-%2d" % abs(special_teams_summary[
            team_id]['special_teams_diff'])
        fore = Fore.LIGHTRED_EX
    else:
        diff_str = "%3d" % 0
        fore = Fore.LIGHTYELLOW_EX

    pp_pctg = (
        special_teams_summary[team.team_id]['ppgf'] /
        special_teams_summary[team.team_id]['pp_opps'] * 100.
    )
    pp_pctgs = "{:4.1f}".format(pp_pctg)

    pk_pctg = 100 - (
        special_teams_summary[team.team_id]['ppga'] /
        special_teams_summary[team.team_id]['tsh'] * 100.
    )
    pk_pctgs = "{:4.1f}".format(pk_pctg)

    pp_pk_pctg = pp_pctg + pk_pctg
    pp_pk_pctgs = "{:5.1f}".format(pp_pk_pctg)

    print("%3d %-22s %4d %4d %4d %4d %4d %s %4d %s %s  %s%s%s" % (
        i, team,
        special_teams_summary[team.team_id]['ppgf'],
        special_teams_summary[team.team_id]['shgf'],
        special_teams_summary[team.team_id]['ppga'],
        special_teams_summary[team.team_id]['shga'],
        special_teams_summary[team.team_id]['pp_opps'], pp_pctgs,
        special_teams_summary[team.team_id]['tsh'], pk_pctgs, pp_pk_pctgs,
        fore, diff_str, Style.RESET_ALL))
    i += 1
