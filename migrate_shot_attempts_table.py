#!/usr/bin/env python

"""
Migrates nhl.shot_attempts from the old "one row per on-ice player per
shot-attempt event" layout (~10.9M rows, ~10GB) to a new "one row per
event" layout with for_player_ids/against_player_ids array columns
(~978k rows).

Run as separate steps so the only risky part (the final rename) is a
single short transaction, independent of how long the (safe, non-locking)
backfill takes:

    python migrate_shot_attempts_table.py --create
    python migrate_shot_attempts_table.py --backfill
    python migrate_shot_attempts_table.py --status
    python migrate_shot_attempts_table.py --cutover

--create and --backfill only ever touch the new nhl.shot_attempts_new
table - they can be run (and --backfill safely re-run, it's idempotent)
at any time while the old nhl.shot_attempts is still being written to by
the *old* parser code. Re-running --backfill only inserts events that
aren't in shot_attempts_new yet, so it doubles as the catch-up step.

--cutover does one final --backfill-equivalent catch-up and the atomic
table rename inside a single transaction, then adds the primary key,
indexes, audit trigger and column comments to the renamed table (added
after the bulk load, not before, since building them once over the full
data set is much faster than maintaining them incrementally during the
backfill). It must only be run once the parser code has already been
switched to the new ShotAttempt shape (db/shot_attempt.py,
parsers/event_parser.py), since from that moment on nhl.shot_attempts IS
what used to be shot_attempts_new. The old table is left in place, renamed
to shot_attempts_old_<timestamp>, for a manual --drop-old afterwards once
you're confident the new table is correct.
"""

import argparse
import sys
from datetime import datetime

from sqlalchemy import text

from db.common import Engine

NEW_TABLE = 'shot_attempts_new'
OLD_TABLE = 'shot_attempts'

CREATE_NEW_TABLE_SQL = f'''
CREATE TABLE IF NOT EXISTS nhl.{NEW_TABLE} (
    shot_attempt_id uuid NOT NULL,
    game_id int4,
    event_id int8 NOT NULL,
    shot_attempt_type char(1) NOT NULL,
    num_situation char(2),
    plr_situation varchar(5),
    score_diff int2,
    for_team_id int4,
    against_team_id int4,
    shooter_id int4,
    for_player_ids int4[],
    against_player_ids int4[]
)
'''

BACKFILL_SQL = f'''
INSERT INTO nhl.{NEW_TABLE}
    (shot_attempt_id, game_id, event_id, shot_attempt_type, num_situation,
     plr_situation, score_diff, for_team_id, against_team_id, shooter_id,
     for_player_ids, against_player_ids)
SELECT
    gen_random_uuid(),
    (array_agg(game_id))[1],
    event_id,
    (array_agg(shot_attempt_type))[1],
    (array_agg(num_situation) FILTER (WHERE plus_minus = 1))[1],
    (array_agg(plr_situation) FILTER (WHERE plus_minus = 1))[1],
    (array_agg(score_diff) FILTER (WHERE plus_minus = 1))[1],
    (array_agg(team_id) FILTER (WHERE plus_minus = 1))[1],
    (array_agg(team_id) FILTER (WHERE plus_minus = -1))[1],
    (array_agg(player_id) FILTER (WHERE actual))[1],
    array_agg(player_id ORDER BY player_id) FILTER (WHERE plus_minus = 1),
    array_agg(player_id ORDER BY player_id) FILTER (WHERE plus_minus = -1)
FROM nhl.{OLD_TABLE}
WHERE event_id NOT IN (SELECT event_id FROM nhl.{NEW_TABLE})
GROUP BY event_id
'''

FINALIZE_NEW_TABLE_SQL = f'''
ALTER TABLE nhl.{NEW_TABLE} ALTER COLUMN shot_attempt_id SET NOT NULL;
ALTER TABLE nhl.{NEW_TABLE} ADD CONSTRAINT shot_attempt_key PRIMARY KEY (shot_attempt_id);
ALTER TABLE nhl.{NEW_TABLE} ADD CONSTRAINT type_check CHECK (shot_attempt_type in ('S', 'M', 'B'));

CREATE UNIQUE INDEX shot_attempt_event_id_idx ON nhl.{NEW_TABLE} USING BTREE (event_id);
CREATE INDEX shot_attempt_game_id_idx ON nhl.{NEW_TABLE} USING BTREE (game_id);
CREATE INDEX shot_attempt_for_player_ids_gin_idx ON nhl.{NEW_TABLE} USING GIN (for_player_ids);
CREATE INDEX shot_attempt_against_player_ids_gin_idx ON nhl.{NEW_TABLE} USING GIN (against_player_ids);

ALTER TABLE nhl.{NEW_TABLE} OWNER TO nhl_user;

COMMENT ON COLUMN nhl.{NEW_TABLE}.game_id IS 'Related game ID';
COMMENT ON COLUMN nhl.{NEW_TABLE}.event_id IS 'Related event ID (one row per shot-attempt event)';
COMMENT ON COLUMN nhl.{NEW_TABLE}.shot_attempt_type IS 'Type of the shot attempt, e.g. (M)iss, (B)lock or (S)hot on Goal';
COMMENT ON COLUMN nhl.{NEW_TABLE}.num_situation IS 'Official numerical situation at the time of the shot attempt event, from the shooting team''s perspective, e.g. EV, PP or SH';
COMMENT ON COLUMN nhl.{NEW_TABLE}.plr_situation IS 'Actual numerical situation at the time of the shot attempt event, from the shooting team''s perspective, e.g. 5v5, 5v4, 6v5 etc.';
COMMENT ON COLUMN nhl.{NEW_TABLE}.score_diff IS 'Score differential at the time of the shot attempt event as registered by the shooting team';
COMMENT ON COLUMN nhl.{NEW_TABLE}.for_team_id IS 'Team that attempted the shot';
COMMENT ON COLUMN nhl.{NEW_TABLE}.against_team_id IS 'Opposing team';
COMMENT ON COLUMN nhl.{NEW_TABLE}.shooter_id IS 'Player who actually took the shot attempt (or, for a blocked shot, whose shot got blocked)';
COMMENT ON COLUMN nhl.{NEW_TABLE}.for_player_ids IS 'Skaters/goalie of the shooting team on the ice for this shot attempt, sorted';
COMMENT ON COLUMN nhl.{NEW_TABLE}.against_player_ids IS 'Skaters/goalie of the opposing team on the ice for this shot attempt, sorted';
'''


def create():
    with Engine.begin() as conn:
        conn.execute(text(CREATE_NEW_TABLE_SQL))
    print(f"+ nhl.{NEW_TABLE} created (or already existed)")


def backfill():
    with Engine.begin() as conn:
        result = conn.execute(text(BACKFILL_SQL))
    print(f"+ Backfilled {result.rowcount} new event(s) into nhl.{NEW_TABLE}")


def status():
    with Engine.connect() as conn:
        old_count = conn.execute(text(
            f'SELECT count(DISTINCT event_id) FROM nhl.{OLD_TABLE}')).scalar()
        try:
            new_count = conn.execute(text(
                f'SELECT count(*) FROM nhl.{NEW_TABLE}')).scalar()
        except Exception:
            new_count = None
    print(f"distinct event_ids in nhl.{OLD_TABLE}: {old_count}")
    print(f"rows in nhl.{NEW_TABLE}: {new_count}")
    if new_count is not None:
        print(f"remaining to backfill: {old_count - new_count}")


def cutover():
    with Engine.connect() as conn:
        old_count = conn.execute(text(
            f'SELECT count(DISTINCT event_id) FROM nhl.{OLD_TABLE}')).scalar()

    old_backup_name = f"{OLD_TABLE}_old_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with Engine.begin() as conn:
        # final catch-up for anything added to the old table since the
        # last --backfill run
        result = conn.execute(text(BACKFILL_SQL))
        print(f"+ Final catch-up backfilled {result.rowcount} event(s)")

        new_count = conn.execute(text(
            f'SELECT count(*) FROM nhl.{NEW_TABLE}')).scalar()
        if new_count != old_count:
            raise RuntimeError(
                f"Refusing to cut over: nhl.{NEW_TABLE} has {new_count} rows, "
                f"but nhl.{OLD_TABLE} has {old_count} distinct event_ids. "
                "Investigate before retrying.")

        conn.execute(text(
            f'ALTER TABLE nhl.{OLD_TABLE} RENAME TO {old_backup_name}'))
        conn.execute(text(
            f'ALTER TABLE nhl.{NEW_TABLE} RENAME TO {OLD_TABLE}'))
        conn.execute(text(FINALIZE_NEW_TABLE_SQL.replace(NEW_TABLE, OLD_TABLE)))
        conn.execute(text(f'''
            CREATE TRIGGER shot_attempts_audit AFTER INSERT OR UPDATE OR DELETE
                ON nhl.{OLD_TABLE} FOR EACH ROW
                EXECUTE PROCEDURE nhl.tr_log_actions()
        '''))

    print(f"+ Cutover complete: nhl.{OLD_TABLE} is now the new, compact table")
    print(f"+ Previous table kept as nhl.{old_backup_name} - drop it manually once verified")


def drop_old(table_name):
    if not table_name.startswith(f"{OLD_TABLE}_old_"):
        print(f"+ Refusing to drop '{table_name}': doesn't look like a "
              f"backed-up old shot_attempts table")
        sys.exit(1)
    with Engine.begin() as conn:
        conn.execute(text(f'DROP TABLE nhl.{table_name}'))
    print(f"+ Dropped nhl.{table_name}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Migrates nhl.shot_attempts to a compact, one-row-per-event layout.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--create', action='store_true', help="Create the new (bare) table")
    group.add_argument('--backfill', action='store_true', help="Backfill/catch-up from the old table")
    group.add_argument('--status', action='store_true', help="Show migration progress")
    group.add_argument('--cutover', action='store_true', help="Final catch-up + atomic rename")
    group.add_argument('--drop-old', dest='drop_old', metavar='TABLE_NAME',
                        help="Drop a shot_attempts_old_* table after verifying the cutover")
    args = parser.parse_args()

    if args.create:
        create()
    elif args.backfill:
        backfill()
    elif args.status:
        status()
    elif args.cutover:
        cutover()
    elif args.drop_old:
        drop_old(args.drop_old)
