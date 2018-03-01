#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import re
from datetime import date
from operator import attrgetter
from itertools import groupby
from collections import defaultdict, OrderedDict

from dateutil.parser import parse
from colorama import Fore, init, Style
from sqlalchemy import cast, String

from db.common import session_scope
from db.team import Team
from db.game import Game
from db.team_game import TeamGame
from db.division import Division


STREAK_REGEX = re.compile(R"(\w)\1*")
MAX_LINE_LENGTH = 76


def get_data(season):
    """
    Retrieves necessary data for specified season.
    """
    # retrieving all team games for specified season
    with session_scope() as session:
        team_games = session.query(
            TeamGame).filter(cast(
                TeamGame.game_id, String).like("%d02%%" % season)).all()

        last_game_date = max(map(
            attrgetter('date'),
            session.query(Game).filter(Game.season == season).all()))

    return team_games, last_game_date


def get_divisions(game_date):
    """
    Retrieves divisions from season of specified date.
    """
    if game_date is None:
        game_date = date.today()

    season = game_date.year

    if game_date.month <= 6:
        season -= 1

    with session_scope() as session:
        divisions = session.query(Division).filter(
            Division.season == season).all()

    return divisions


def get_data_for_interval(from_date, to_date, include_playoffs=False):
    """
    Retrieves team games for specified interval.
    """

    filters = [
        Game.game_id == TeamGame.game_id,
        Game.date >= from_date,
        Game.date <= to_date
    ]

    if not include_playoffs:
        filters.append(Game.type == 2)

    with session_scope() as session:
        team_games = session.query(TeamGame, Game).filter(*filters).all()

    return [tg[0] for tg in team_games]


def compile_records(team_games):
    """
    Compiles team records from specified team-per-game items.
    """
    records = dict()

    for tg in sorted(team_games):
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
        # aggregating official regulation or overtime wins (row)
        if any([tg.regulation_win, tg.overtime_win]):
            records[tg.team_id]['orow'] += 1
        # *regulation* rows are just regulation wins
        records[tg.team_id]['row'] = records[tg.team_id]['w']
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
        # decreasing regulation goal totals by empty-net goals for and against
        records[tg.team_id]['gf'] -= tg.empty_net_goals_for
        records[tg.team_id]['ga'] -= tg.empty_net_goals_against
        # decreasing regulation goal totals by overtime goals for and against
        if tg.overtime_win:
            records[tg.team_id]['gf'] -= 1
        if tg.overtime_loss:
            records[tg.team_id]['ga'] -= 1
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
        # calculating point percentages
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


def group_records(records):
    """
    Groups records by league, conference and division.
    """
    grouped_records = dict()
    # grouping records by league
    grouped_records['league'] = records
    # grouping records by conference
    for value, group in groupby(records.items(), lambda x: x[1]['conference']):
        if value not in grouped_records:
            grouped_records[value] = dict()
        grouped_records[value].update(group)
    # grouping records by division
    for value, group in groupby(records.items(), lambda x: x[1]['division']):
        if value not in grouped_records:
            grouped_records[value] = dict()
        grouped_records[value].update(group)

    return grouped_records


def sort_records(records, type='official', max_number=None):
    """
    Sorts records by specified sorting type. Optionally constrains output to
    specified maximum number of teams.
    """
    sorted_records = OrderedDict()

    if type == 'official':
        key_prefix = 'o'
    elif type == 'regulation':
        key_prefix = ''

    sorted_records_keys = sorted(records, key=lambda x: (
        records[x]["%spts" % key_prefix],
        records[x]["%sppctg" % key_prefix],
        records[x]["%srow" % key_prefix],
        records[x]["%sgd" % key_prefix],
        records[x]["%sgf" % key_prefix]), reverse=True)

    if max_number:
        upper_limit = max_number
    else:
        upper_limit = len(records)

    for team_id in sorted_records_keys[:upper_limit]:
        sorted_records[team_id] = records[team_id]

    return sorted_records


def prepare_output(records, type='official'):
    """
    Prepares output of specified (and usually sorted) records.
    """
    if type == 'official':
        key_prefix = 'o'
        otl_tie_key = 'otl'
        otl_tie_header = 'OT'
    elif type == 'regulation':
        key_prefix = ''
        otl_tie_key = 't'
        otl_tie_header = 'T'

    rank = 1
    output = list()
    # creating header with column titles
    output.append(format(
        "  # %-22s %2s %2s %2s %2s %3s %3s %3s %4s %s %-15s %s" % (
            'Team', 'GP', 'W', 'L', otl_tie_header, 'Pts', 'GF', 'GA', 'GD',
            'CS', 'Seq 15', 'L 10')))

    for team_id in records:
        team = Team.find_by_id(team_id)
        gd, fore = get_colored_output(records[team_id]["%sgd" % key_prefix])
        sequence = get_colored_sequence(
            records[team_id]["%ssequence" % key_prefix])
        streak = get_colored_streak(records[team_id]["%sstreak" % key_prefix])
        recent_record = get_recent_record(
            records[team_id]["%ssequence" % key_prefix])

        s = format("%3d %-22s %2d %2d %2d %2d %3d %3d-%3d %s%s%s %s %s %s" % (
            rank, team, records[team_id]['gp'],
            records[team_id]["%sw" % key_prefix],
            records[team_id]['ol'],
            records[team_id]["%s%s" % (key_prefix, otl_tie_key)],
            records[team_id]["%spts" % key_prefix],
            records[team_id]["%sgf" % key_prefix],
            records[team_id]["%sga" % key_prefix],
            fore, gd, Style.RESET_ALL, streak, sequence, recent_record,
            ))

        output.append(s)
        rank += 1

    return "\n".join(output)


def get_current_streak(sequence):
    """
    Retrieves most current streak from specified sequence of game outcomes.
    """
    curr_streak = [m.group(0) for m in re.finditer(STREAK_REGEX, sequence)][-1]
    return "%s%d" % (curr_streak[0], len(curr_streak))


def get_recent_record(sequence, length=10):
    """
    Retrieves record in last number of games, specified by provided length.
    """
    wins = sequence[-length:].count('W')
    losses = sequence[-length:].count('L')
    overtime_losses = sequence[-length:].count('O')
    ties = sequence[-length:].count('T')

    return "%d-%d-%d" % (wins, losses, overtime_losses + ties)


def get_colored_sequence(sequence, length=15):
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


def get_colored_output(criterion):
    """
    Returns color-coded output based on specified criterion being larger than,
    less than or equal to zero.
    """
    if criterion > 0:
        criterion_as_string = "+%3d" % criterion
        color = Fore.LIGHTGREEN_EX
    elif criterion < 0:
        criterion_as_string = "-%3d" % abs(criterion)
        color = Fore.LIGHTRED_EX
    else:
        criterion_as_string = "%4d" % 0
        color = Fore.LIGHTYELLOW_EX
    return criterion_as_string, color


def get_date_string(from_date, to_date):
    """
    Retrieves string-formatted date either for the interval between from_date
    and to_date or solely for to_date (if from_date is None).
    """
    if from_date is not None:
        return " - ".join((
            from_date.strftime("%b %d, %Y"), to_date.strftime("%b %d, %Y")))
    else:
        return to_date.strftime("%b %d, %Y")


def get_league_standings(records, ranking_type, from_date, to_date):
    """
    Gets overall league standings using specified records.
    """
    print(
        " + NHL %s Standings (%s)" % (
            ranking_type.capitalize(),
            get_date_string(from_date, to_date)))
    sorted_records = sort_records(records['league'], type=ranking_type)
    print(prepare_output(sorted_records, type=ranking_type))


def get_conference_standings(records, rankings_type, from_date, to_date):
    """
    Gets conference standngs using specified records.
    """
    for conference in ['Eastern', 'Western']:
        print(" + %s Conference %s Standings (%s)" % (
            conference, ranking_type.capitalize(),
            get_date_string(from_date, to_date)))
        sorted_records = sort_records(records[conference], type=ranking_type)
        print(prepare_output(sorted_records, type=ranking_type))
        print()


def get_division_standings(
        records, ranking_type, divisions, from_date, to_date):
    """
    Gets division standings using specified records
    """
    # printing division records
    for division in sorted(divisions):
        print(" + %s Division %s Standings (%s)" % (
            division.division_name, ranking_type.capitalize(),
            get_date_string(from_date, to_date)))
        sorted_records = sort_records(
            records[division.division_name], type=ranking_type)
        print(prepare_output(sorted_records, type=ranking_type))
        print()


def get_wildcard_standings(
        records, ranking_type, divisions, from_date, to_date):
    """
    Gets wildcard standings using specified records.
    """
    for conference in ['Eastern', 'Western']:
        print(" + %s Conference %s Wild Card Standings (%s)" % (
            conference, ranking_type.capitalize(),
            get_date_string(from_date, to_date)))
        # sorting records in conference
        sorted_records = sort_records(
            records[conference], type=ranking_type)
        for division in sorted(divisions):
            # only considering divisions in current conference
            if division.conference == conference:
                print(" + %s Division:" % division.division_name)
                # sorting records in division, yielding first three only
                sorted_by_division = sort_records(
                    records[division.division_name],
                    type=ranking_type,
                    max_number=3)
                # printing first three in division
                print(
                    prepare_output(sorted_by_division, type=ranking_type))
                # removing teams from sorted division in conference
                for team_id in sorted_by_division:
                    del sorted_records[team_id]
        print(" + %s Conference Wild Card" % conference)
        # printing remaining teams in conference
        print(prepare_output(sorted_records, type=ranking_type))
        print()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='NHL official and regulation standings for given season')
    parser.add_argument(
        'season', metavar='season', help='Season selection for standings.',
        default=2017, nargs='?', type=int)
    parser.add_argument(
        '-f', '--from', dest='from_date', required=False,
        metavar='first date to retrieve standings for',
        help='The date from which on standings will be retrieved')
    parser.add_argument(
        '-t', '--to', dest='to_date', required=False,
        metavar='last date to retrieve standings for',
        help='The date to which to standings will be retrieved')
    parser.add_argument(
        '--sequence', dest='sequence', required=False, type=int, default=15,
        metavar='Length of game sequence to present streak information for'
    )
    parser.add_argument(
        '--regulation', dest='regulation', required=False,
        action='store_true',
        help='Include regulation standings in output')
    parser.add_argument(
        '-s', '--standings', dest='standings', required=False,
        choices=['all', 'league', 'conference', 'division', 'wildcard'],
        default='wildcard', help='Type of standings to be displayed')

    args = parser.parse_args()
    season = args.season
    sequence = args.sequence
    standings = args.standings

    if args.from_date:
        from_date = parse(args.from_date)
    else:
        from_date = None
    if args.to_date:
        to_date = parse(args.to_date)
    else:
        from_date = None

    if from_date is not None and to_date is None:
        to_date = date.today()

    if from_date is not None:
        team_games = get_data_for_interval(from_date, to_date)
    else:
        team_games, to_date = get_data(season)

    divisions = get_divisions(from_date)

    records = compile_records(team_games)

    # adding team's division and conference to each record
    for team_id in records:
        for division in divisions:
            if team_id in division.teams:
                records[team_id]['division'] = division.division_name
                records[team_id]['conference'] = division.conference
                break

    # grouping records by league/division/conference
    grouped_records = group_records(records)

    ranking_types = ['official']
    if args.regulation:
        ranking_types.append('regulation')

    # printing records of both ranking types
    init()

    for ranking_type in ranking_types:
        print()

        if standings in ['all', 'league']:
            # printing overall records of current ranking type
            get_league_standings(
                grouped_records, ranking_type, from_date, to_date)
            print()
            print(MAX_LINE_LENGTH * "-")
            print()

        if standings in ['all', 'conference']:
            # printing conference records
            get_conference_standings(
                grouped_records, ranking_type, from_date, to_date)
            print(MAX_LINE_LENGTH * "-")
            print()

        if standings in ['all', 'wildcard']:
            # printing conference records in wild card mode
            get_wildcard_standings(
                grouped_records, ranking_type, divisions, from_date, to_date)
            print(MAX_LINE_LENGTH * "-")
            print()

        if standings in ['all', 'divisions']:
            # printing division records
            get_division_standings(
                grouped_records, ranking_type, divisions, from_date, to_date)
            print(MAX_LINE_LENGTH * "=")
