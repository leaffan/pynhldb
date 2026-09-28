#!/usr/bin/env python

import json
import os


class PendingParseTracker:
    """
    Tracks, per date, the ids of games whose raw downloaded data has changed
    since it was last successfully parsed. Backed by a JSON file living
    alongside the downloaded summary data (analogous to
    SummaryDownloader's `_mod_timestamps.json`).

    A download run and a parse run may be in progress at the same time (e.g.
    in two separate processes), each holding their own instance of this
    tracker. To avoid one of them clobbering the other's update when both
    eventually save, each instance only records the changes it made itself
    (`_changed`/`_parsed`) and, on `save()`, re-reads the current on-disk
    state and replays just those changes onto it, rather than overwriting
    the file with a potentially stale in-memory snapshot.
    """

    FILE_NAME = '_pending_parse.json'

    def __init__(self, tgt_dir):
        self.src = os.path.join(tgt_dir, self.FILE_NAME)
        self.pending = self._load()
        # changes recorded by this instance since construction, replayed
        # onto the latest on-disk state at save() time
        self._changed = {}
        self._parsed = {}

    def _load(self):
        if os.path.isfile(self.src):
            with open(self.src) as f:
                return json.load(f)
        return {}

    def mark_changed(self, date_str, game_ids):
        """
        Registers the specified game ids as having changed raw data for the
        given date (YYYY-MM-DD), e.g. after (re-)downloading them.
        """
        if not game_ids:
            return
        existing = set(self.pending.get(date_str, []))
        existing.update(game_ids)
        self.pending[date_str] = sorted(existing)

        self._changed.setdefault(date_str, set()).update(game_ids)
        self._parsed.get(date_str, set()).difference_update(game_ids)

    def get_pending(self, date_str):
        """
        Returns the ids of games with changed raw data for the given date.
        """
        return set(self.pending.get(date_str, []))

    def mark_parsed(self, date_str, game_ids):
        """
        Removes the specified game ids from the set of games with changed
        raw data for the given date, i.e. after they have been parsed
        successfully.
        """
        if not game_ids:
            return
        if date_str in self.pending:
            remaining = set(self.pending[date_str]) - set(game_ids)
            if remaining:
                self.pending[date_str] = sorted(remaining)
            else:
                del self.pending[date_str]

        self._parsed.setdefault(date_str, set()).update(game_ids)
        self._changed.get(date_str, set()).difference_update(game_ids)

    def save(self):
        """
        Merges this instance's own changes onto the latest on-disk state and
        writes the result back, instead of overwriting the file with this
        instance's (possibly stale) in-memory snapshot. This keeps a
        concurrently running download or parse process (in another instance
        of this tracker) from having its updates silently lost.
        """
        current = self._load()

        for date_str, ids in self._changed.items():
            if not ids:
                continue
            existing = set(current.get(date_str, []))
            existing.update(ids)
            current[date_str] = sorted(existing)

        for date_str, ids in self._parsed.items():
            if not ids or date_str not in current:
                continue
            remaining = set(current[date_str]) - ids
            if remaining:
                current[date_str] = sorted(remaining)
            else:
                del current[date_str]

        with open(self.src, 'w') as f:
            json.dump(current, f, indent=2, sort_keys=True)

        self.pending = current
        self._changed.clear()
        self._parsed.clear()
