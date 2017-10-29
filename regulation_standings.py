
from collections import defaultdict

from colorama import Fore, init, Style
from sqlalchemy import cast, String

from db.common import session_scope
from db.team_game import TeamGame
from db.team import Team
from db.division import Division

season = 2017

# retrieving all team games for specified season
with session_scope() as session:
    team_games = session.query(
        TeamGame).filter(cast(
            TeamGame.game_id, String).like("%d02%%" % season)).all()

    divisions = session.query(Division).filter(Division.season == season).all()

# TODO
# rank by division, conference etc.

summary = dict()

for tg in team_games:
    if tg.team_id not in summary:
        summary[tg.team_id] = defaultdict(int)
    # aggregating games played
    summary[tg.team_id]['gp'] += 1
    # aggregating official goals for and against
    summary[tg.team_id]['ogf'] += tg.score
    summary[tg.team_id]['oga'] += tg.score_against
    # aggregating actual goals for and against
    summary[tg.team_id]['gf'] += tg.goals_for
    summary[tg.team_id]['ga'] += tg.goals_against
    # aggregating official wins and losses
    summary[tg.team_id]['ow'] += tg.win
    summary[tg.team_id]['ol'] += tg.regulation_loss
    if any([tg.shootout_loss, tg.overtime_loss]):
        summary[tg.team_id]['ootl'] += 1
    # aggregating regulation wins
    summary[tg.team_id]['w'] += tg.regulation_win
    # aggregating ties, i.e. games that went to overtime or shootout
    if any([
            tg.overtime_win, tg.shootout_win,
            tg.overtime_loss, tg.shootout_loss]):
                summary[tg.team_id]['t'] += 1
    # decreasing actual goals scored by one for an overtime win
    if tg.overtime_win:
        summary[tg.team_id]['gf'] -= 1
    # decreasing actual goal totals by empty-net goals for and against
    summary[tg.team_id]['gf'] -= tg.empty_net_goals_for
    summary[tg.team_id]['ga'] -= tg.empty_net_goals_against
    # calculating goal differentials
    summary[tg.team_id]['ogd'] = (
        summary[tg.team_id]['ogf'] - summary[tg.team_id]['oga'])
    summary[tg.team_id]['gd'] = (
        summary[tg.team_id]['gf'] - summary[tg.team_id]['ga'])
    # calculating points
    summary[tg.team_id]['opts'] = (
        summary[tg.team_id]['ow'] * 2 + summary[tg.team_id]['ootl'])
    summary[tg.team_id]['pts'] = (
        summary[tg.team_id]['w'] * 2 + summary[tg.team_id]['t'])
    # calculating point percentage
    summary[tg.team_id]['oppctg'] = round(
        summary[tg.team_id]['opts'] / (summary[tg.team_id]['gp'] * 2.0), 3)
    summary[tg.team_id]['ppctg'] = round(
        summary[tg.team_id]['pts'] / (summary[tg.team_id]['gp'] * 2.0), 3)

i = 1

init()
print()


print("  # %-22s %2s %2s %2s %2s %3s %3s %3s %3s" % (
    'Team', 'GP', 'W', 'L', 'OT', 'Pts', 'GF', 'GA', 'GD'))

for team_id in sorted(summary, key=lambda x: (
        summary[x]['opts'], summary[x]['oppctg'], summary[x]['ow'],
        summary[x]['ogd'], summary[x]['ogf']), reverse=True):
    team = Team.find_by_id(team_id)
    if summary[team_id]['ogd'] > 0:
        gd = "+%2d" % summary[team_id]['ogd']
        fore = Fore.LIGHTGREEN_EX
    elif summary[team_id]['ogd'] < 0:
        gd = "-%2d" % abs(summary[team_id]['ogd'])
        fore = Fore.LIGHTRED_EX
    else:
        gd = "%3d" % 0
        fore = Fore.LIGHTYELLOW_EX

    # saving official ranking
    summary[team_id]['orank'] = i

    print("%3d %-22s %2d %2d %2d %2d %3d %3d-%3d %s%s%s" % (
        i, team, summary[team_id]['gp'], summary[team_id]['ow'],
        summary[team_id]['ol'], summary[team_id]['ootl'],
        summary[team_id]['opts'],
        summary[team_id]['ogf'], summary[team_id]['oga'],
        fore, gd, Style.RESET_ALL))
    i += 1

print()
i = 1

print("  # (O#) %-22s %2s %2s %2s %2s %3s %3s %3s %3s" % (
    'Team', 'GP', 'W', 'L', 'T', 'Pts', 'GF', 'GA', 'GD'))
for team_id in sorted(summary, key=lambda x: (
        summary[x]['pts'], summary[x]['ppctg'], summary[x]['w'],
        summary[x]['gd'], summary[x]['gf']), reverse=True):
    team = Team.find_by_id(team_id)
    # determining output format for goal differential
    if summary[team_id]['gd'] > 0:
        gd = "+%2d" % summary[team_id]['gd']
        fore = Fore.LIGHTGREEN_EX
    elif summary[team_id]['gd'] < 0:
        gd = "-%2d" % abs(summary[team_id]['gd'])
        fore = Fore.LIGHTRED_EX
    else:
        gd = "%3d" % 0
        fore = Fore.LIGHTYELLOW_EX

    print("%3d (%2d) %-22s %2d %2d %2d %2d %3d %3d-%3d %s%s%s" % (
        i, summary[team_id]['orank'], team, summary[team_id]['gp'],
        summary[team_id]['w'], summary[team_id]['ol'], summary[team_id]['t'],
        summary[team_id]['pts'],
        summary[team_id]['gf'], summary[team_id]['ga'],
        fore, gd, Style.RESET_ALL))
    i += 1

print()
