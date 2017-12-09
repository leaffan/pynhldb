#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from operator import attrgetter
from itertools import groupby
from collections import defaultdict

from colorama import Fore, init, Style
from sqlalchemy import cast, String

from db.common import session_scope
from db.team import Team
from db.game import Game
from db.team_game import TeamGame
from db.division import Division

# TODO: wild card rankings

STREAK_REGEX = re.compile(R"(\w)\1*")


def get_data(season):
    # retrieving all team games for specified season
    with session_scope() as session:
        team_games = session.query(
            TeamGame).filter(cast(
                TeamGame.game_id, String).like("%d02%%" % season)).all()

        divisions = session.query(Division).filter(
            Division.season == season).all()

        last_game_date = max(map(
            attrgetter('date'),
            session.query(Game).filter(Game.season == season).all()))

    return team_games, divisions, last_game_date


def get_colored_output(criterion):
    # determining output color in dependance of selected criterion being larger
    # than, less than or equal to zero
    if criterion > 0:
        criterion_as_string = "+%2d" % criterion
        color = Fore.LIGHTGREEN_EX
    elif criterion < 0:
        criterion_as_string = "-%2d" % abs(criterion)
        color = Fore.LIGHTRED_EX
    else:
        criterion_as_string = "%3d" % 0
        color = Fore.LIGHTYELLOW_EX
    return criterion_as_string, color


def get_teams_by_division_conference(divisions):
    teams_by_division = defaultdict(list)
    teams_by_conference = defaultdict(list)

    for division in divisions:
        teams_by_division[division.division_name] += division.teams
        if division.conference:
            teams_by_division[division.conference] += division.teams

    return teams_by_division, teams_by_conference


def compile_records(team_games):
    records = dict()

    for tg in team_games:
        if tg.team_id not in records:
            records[tg.team_id] = defaultdict(int)
        # aggregating games played
        records[tg.team_id]['gp'] += 1
        # aggregating official goals for and against
        records[tg.team_id]['ogf'] += tg.score
        records[tg.team_id]['oga'] += tg.score_against
        # aggregating actual goals for and against
        records[tg.team_id]['gf'] += tg.goals_for
        records[tg.team_id]['ga'] += tg.goals_against
        # aggregating official wins and losses
        records[tg.team_id]['ow'] += tg.win
        records[tg.team_id]['ol'] += tg.regulation_loss
        if any([tg.shootout_loss, tg.overtime_loss]):
            records[tg.team_id]['ootl'] += 1
        # aggregating regulation wins
        records[tg.team_id]['w'] += tg.regulation_win
        # aggregating ties, i.e. games that went to overtime or shootout
        if any([
                tg.overtime_win, tg.shootout_win,
                tg.overtime_loss, tg.shootout_loss]):
                    records[tg.team_id]['t'] += 1
        # decreasing actual goals scored by one for an overtime win
        if tg.overtime_win:
            records[tg.team_id]['gf'] -= 1
        # decreasing actual goals allowed by one for an overtime loss
        if tg.overtime_loss:
            records[tg.team_id]['ga'] -= 1
        # decreasing actual goal totals by empty-net goals for and against
        records[tg.team_id]['gf'] -= tg.empty_net_goals_for
        records[tg.team_id]['ga'] -= tg.empty_net_goals_against
        # calculating goal differentials
        records[tg.team_id]['ogd'] = (
            records[tg.team_id]['ogf'] - records[tg.team_id]['oga'])
        records[tg.team_id]['gd'] = (
            records[tg.team_id]['gf'] - records[tg.team_id]['ga'])
        # calculating points
        records[tg.team_id]['opts'] = (
            records[tg.team_id]['ow'] * 2 + records[tg.team_id]['ootl'])
        records[tg.team_id]['pts'] = (
            records[tg.team_id]['w'] * 2 + records[tg.team_id]['t'])
        # calculating point percentage
        records[tg.team_id]['oppctg'] = round(
            records[tg.team_id]['opts'] / (
                records[tg.team_id]['gp'] * 2.0), 3)
        records[tg.team_id]['ppctg'] = round(
            records[tg.team_id]['pts'] / (
                records[tg.team_id]['gp'] * 2.0), 3)
        # registering sequence of official game outcomes, denoting overtime/
        # shootout losses separately
        if not records[tg.team_id]['osequence']:
            records[tg.team_id]['osequence'] = ''
        if tg.win:
            records[tg.team_id]['osequence'] += 'W'
        elif tg.regulation_loss:
            records[tg.team_id]['osequence'] += 'L'
        elif tg.loss:
            records[tg.team_id]['osequence'] += 'O'

        records[tg.team_id]['ostreak'] = get_current_streak(
            records[tg.team_id]['osequence'])

        # registering sequence of regulation game outcomes, denoting overtime/
        # shootout games as ties
        if not records[tg.team_id]['sequence']:
            records[tg.team_id]['sequence'] = ''
        if tg.regulation_win:
            records[tg.team_id]['sequence'] += 'W'
        elif tg.regulation_loss:
            records[tg.team_id]['sequence'] += 'L'
        else:
            records[tg.team_id]['sequence'] += 'T'

        records[tg.team_id]['streak'] = get_current_streak(
            records[tg.team_id]['sequence'])

    return records


def get_current_streak(sequence):
    curr_streak = [m.group(0) for m in re.finditer(STREAK_REGEX, sequence)][-1]
    return "%s%d" % (curr_streak[0], len(curr_streak))


def prepare_sorted_output(records, group=None, type='official'):
    """
    Prepares sorted output of specified records.
    """
    if type == 'official':
        key_prefix = 'o'
        otl_tie_key = 'otl'
        otl_tie_header = 'OT'
        sorted_team_ids = sorted(records, key=lambda x: (
            records[x]["%spts" % key_prefix],
            records[x]["%sppctg" % key_prefix],
            records[x]["%sw" % key_prefix],
            records[x]["%sgd" % key_prefix],
            records[x]["%sgf" % key_prefix]), reverse=True)
    elif type == 'regulation':
        key_prefix = ''
        otl_tie_key = 't'
        otl_tie_header = 'T'
        sorted_team_ids = sorted(records, key=lambda x: (
            records[x]["%spts" % key_prefix],
            records[x]["%sppctg" % key_prefix],
            records[x]["%sw" % key_prefix],
            records[x]["%sgd" % key_prefix],
            records[x]["%sgf" % key_prefix]), reverse=True)

    rank = 1
    output = list()
    # creating header with column titles
    output.append(format(
        "  # %-22s %2s %2s %2s %2s %3s %3s %3s %3s" % (
            'Team', 'GP', 'W', 'L', otl_tie_header, 'Pts', 'GF', 'GA', 'GD')))

    for team_id in sorted_team_ids:
        team = Team.find_by_id(team_id)
        gd, fore = get_colored_output(records[team_id]["%sgd" % key_prefix])
        sequence = get_colored_sequence(
            records[team_id]["%ssequence" % key_prefix])
        streak = get_colored_streak(records[team_id]["%sstreak" % key_prefix])

        s = format("%3d %-22s %2d %2d %2d %2d %3d %3d-%3d %s%s%s %s %s" % (
            rank, team, records[team_id]['gp'],
            records[team_id]["%sw" % key_prefix],
            records[team_id]['ol'],
            records[team_id]["%s%s" % (key_prefix, otl_tie_key)],
            records[team_id]["%spts" % key_prefix],
            records[team_id]["%sgf" % key_prefix],
            records[team_id]["%sga" % key_prefix],
            fore, gd, Style.RESET_ALL, streak, sequence
            ))

        output.append(s)
        rank += 1

    return "\n".join(output)


def get_colored_sequence(sequence, length=5):
    """
    Returns color-coded sequence of game outcomes.
    """
    output = ""
    for single_game in sequence[-length:]:
        if single_game == 'W':
            output += Fore.LIGHTGREEN_EX + single_game
        elif single_game in ('O', 'T'):
            output += Fore.LIGHTYELLOW_EX + single_game
        elif single_game == 'L':
            output += Fore.LIGHTRED_EX + single_game
    else:
        output += Style.RESET_ALL

    if len(sequence) < length:
        output = "".join(((length - len(sequence)) * '-', output))

    return output


def get_colored_streak(streak):
    """
    Returns color-coded streak of most recent game outcomes.
    """
    output = ""
    if streak[0] == 'W':
        output += Fore.LIGHTGREEN_EX + streak
    elif streak[0] in ('O', 'T'):
        output += Fore.LIGHTYELLOW_EX + streak
    elif streak[0] == 'L':
        output += Fore.LIGHTRED_EX + streak
    output += Style.RESET_ALL

    return output


if __name__ == '__main__':

    season = 2017

    team_games, divisions, last_game_date = get_data(season)
    records = compile_records(team_games)

    # adding team's division and conference to each record
    for team_id in records:
        for division in divisions:
            if team_id in division.teams:
                records[team_id]['division'] = division.division_name
                records[team_id]['conference'] = division.conference
                break

    # grouping records by division/conference
    grouped_records = dict()

    for value, group in groupby(records.items(), lambda x: x[1]['conference']):
        if value not in grouped_records:
            grouped_records[value] = dict()
        grouped_records[value].update(group)

    for value, group in groupby(records.items(), lambda x: x[1]['division']):
        if value not in grouped_records:
            grouped_records[value] = dict()
        grouped_records[value].update(group)

    # printing records of both ranking types
    init()

    for ranking_type in ('official', 'regulation'):
        print()
        # printing overall records of current ranking type
        print(
            " + NHL %s Standings (%s)" % (
                ranking_type.capitalize(),
                last_game_date.strftime("%b %d, %Y")))
        print(prepare_sorted_output(records, type=ranking_type))
        print()

        # printing official conference records
        for conference in ['Eastern', 'Western']:
            print(" + %s Conference %s Standings (%s)" % (
                conference, ranking_type.capitalize(),
                last_game_date.strftime("%b %d, %Y")))
            print(prepare_sorted_output(
                grouped_records[conference], type=ranking_type))
            print()

        # printing official division records
        for division in divisions:
            print(" + %s Division %s Standings (%s)" % (
                division.division_name, ranking_type.capitalize(),
                last_game_date.strftime("%b %d, %Y")))
            print(prepare_sorted_output(
                grouped_records[division.division_name], type=ranking_type))
            print()

        print("==============================================================")

    # printing regulation overall records
    # TODO: retain official/another ranking
    # saving official ranking
    # records[team_id]['orank'] = i
    # print("  # (O#) %-22s %2s %2s %2s %2s %3s %3s %3s %3s" % (
    #     'Team', 'GP', 'W', 'L', 'T', 'Pts', 'GF', 'GA', 'GD'))
