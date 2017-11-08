#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

from sqlalchemy import cast, String, and_
from colorama import Fore, init, Style

from db.common import session_scope
from db.game import Game
from db.event import Event
from db.goal import Goal
from db.team import Team

season = 2017

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

i = 1
init()
print()
print(" + NHL Special Teams Goal Differential")
print()

print("  # %-22s %4s %4s %4s %4s %4s" % (
    'Team', 'PPGF', 'SHGF', 'PPGA', 'SHGA', 'STGD'))

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

    print("%3d %-22s %4d %4d %4d %4d  %s%s%s" % (
        i, team,
        special_teams_summary[team.team_id]['ppgf'],
        special_teams_summary[team.team_id]['shgf'],
        special_teams_summary[team.team_id]['ppga'],
        special_teams_summary[team.team_id]['shga'],
        fore, diff_str, Style.RESET_ALL))
    i += 1
