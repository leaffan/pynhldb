#!/usr/bin/env python

import json
import os


class PendingParseTracker:
    """
    Tracks, per date, the ids of games whose raw downloaded data has changed
    since it was last successfully parsed. Backed by a JSON file living
    alongside the downloaded summary data (analogous to
    SummaryDownloader's `_mod_timestamps.json`).
    """

    FILE_NAME = '_pending_parse.json'

    def __init__(self, tgt_dir):
        self.src = os.path.join(tgt_dir, self.FILE_NAME)
        if os.path.isfile(self.src):
            with open(self.src) as f:
                self.pending = json.load(f)
        else:
            self.pending = {}

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
        if date_str not in self.pending or not game_ids:
            return
        remaining = set(self.pending[date_str]) - set(game_ids)
        if remaining:
            self.pending[date_str] = sorted(remaining)
        else:
            del self.pending[date_str]

    def save(self):
        with open(self.src, 'w') as f:
            json.dump(self.pending, f, indent=2, sort_keys=True)
