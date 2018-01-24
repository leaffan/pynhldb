import json
import sys
sys.path.append("..")

from collections import defaultdict  # noqa: E402

from db.common import session_scope  # noqa: E402
from db.goal import Goal  # noqa: E402
from db.event import Event  # noqa: E402

LIMIT = 0
TGT_JSON = "goal_distribution.json"

if __name__ == '__main__':

    with session_scope() as session:
        goals = session.query(Goal)

        if LIMIT:
            goals = goals.limit(LIMIT)

        goals = goals.all()

    print("+ %d goals found in database" % len(goals))

    goals_by_time = defaultdict(int)

    i = 0

    for goal in goals[:]:
        i += 1
        event = Event.find_by_id(goal.event_id)
        total_time = (event.period - 1) * 60 * 20 + event.time.seconds
        # goals_by_time[(event.period, event.time.seconds)] += 1
        goals_by_time[total_time] += 1
        if i % (len(goals) // 20) == 0:
            print("+ %d goals processed" % i)

    # for period, time in sorted(goals_by_time.keys()):
    #     print(period, time, goals_by_time[(period, time)])

    for total_time in sorted(goals_by_time.keys()):
        print(total_time, goals_by_time[total_time])

    json.dump(goals_by_time, open(TGT_JSON, 'w'), sort_keys=True, indent=2)
