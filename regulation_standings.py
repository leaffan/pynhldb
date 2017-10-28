
from collections import defaultdict

from colorama import Fore, init, Style
from sqlalchemy import cast, String

from db.common import session_scope
from db.team_game import TeamGame
from db.team import Team

season = 2017

# retrieving all team games for specified season
with session_scope() as session:
    team_games = session.query(
        TeamGame).filter(cast(
            TeamGame.game_id, String).like("%d02%%" % season)).all()

summary = dict()

for tg in team_games:
    if tg.team_id not in summary:
        summary[tg.team_id] = defaultdict(int)
    # aggregating games played, goals for and goals against
    summary[tg.team_id]['gp'] += 1
    summary[tg.team_id]['gf'] += tg.goals_for
    summary[tg.team_id]['ga'] += tg.goals_against
    # aggregating regulation wins or losses
    summary[tg.team_id]['w'] += tg.regulation_win
    summary[tg.team_id]['l'] += tg.regulation_loss
    # adding a tie if this game went to overtime or shootout
    if any([
            tg.overtime_win, tg.shootout_win,
            tg.overtime_loss, tg.shootout_loss]):
                summary[tg.team_id]['t'] += 1
    # calculating goal differential
    summary[tg.team_id]['gd'] = (
        summary[tg.team_id]['gf'] - summary[tg.team_id]['ga'])
    # calculating points
    summary[tg.team_id]['pts'] = (
        summary[tg.team_id]['w'] * 2 + summary[tg.team_id]['t'])

i = 1

init()
print()

# ranking teams sorted by points and wins
print("  # %-22s %2s %2s %2s %3s %3s %3s %3s" % (
    'Team', 'W', 'L', 'T', 'Pts', 'GF', 'GA', 'GD'))
for team_id in sorted(summary, key=lambda x: (
        summary[x]['pts'], summary[x]['w'],
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

    print("%3d %-22s %2d %2d %2d %3d %3d-%3d %s%s%s" % (
        i, team,
        summary[team_id]['w'], summary[team_id]['l'], summary[team_id]['t'],
        summary[team_id]['pts'],
        summary[team_id]['gf'], summary[team_id]['ga'],
        fore, gd, Style.RESET_ALL))
    i += 1

print()
