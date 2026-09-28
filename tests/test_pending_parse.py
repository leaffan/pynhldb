#!/usr/bin/env python

import json
import os

from utils.pending_parse import PendingParseTracker


def test_mark_changed_and_get_pending(tmpdir):

    tracker = PendingParseTracker(tmpdir.strpath)
    tracker.mark_changed('2025-10-08', {'020451', '020452'})

    assert tracker.get_pending('2025-10-08') == {'020451', '020452'}
    assert tracker.get_pending('2025-10-09') == set()


def test_mark_changed_accumulates_across_instances(tmpdir):

    t1 = PendingParseTracker(tmpdir.strpath)
    t1.mark_changed('2025-10-08', {'020451', '020452'})
    t1.save()

    t2 = PendingParseTracker(tmpdir.strpath)
    t2.mark_changed('2025-10-08', {'020452', '020453'})
    t2.save()

    t3 = PendingParseTracker(tmpdir.strpath)
    assert t3.get_pending('2025-10-08') == {'020451', '020452', '020453'}


def test_mark_parsed_removes_only_the_given_games(tmpdir):

    tracker = PendingParseTracker(tmpdir.strpath)
    tracker.mark_changed('2025-10-08', {'020451', '020452', '020453'})
    tracker.mark_parsed('2025-10-08', {'020451', '020452'})

    assert tracker.get_pending('2025-10-08') == {'020453'}


def test_mark_parsed_clears_the_date_entry_once_empty(tmpdir):

    tracker = PendingParseTracker(tmpdir.strpath)
    tracker.mark_changed('2025-10-08', {'020451'})
    tracker.mark_parsed('2025-10-08', {'020451'})
    tracker.save()

    with open(os.path.join(tmpdir.strpath, '_pending_parse.json')) as f:
        data = json.load(f)

    assert data == {}


def test_concurrent_download_and_parse_do_not_clobber_each_other(tmpdir):
    # regression test for a race condition: a download run and a parse run
    # each hold their own tracker instance and may save at different times;
    # neither must lose the other's update
    root = tmpdir.strpath
    date = '2025-10-08'

    seed = PendingParseTracker(root)
    seed.mark_changed(date, {'020451', '020452', '020453'})
    seed.save()

    parse_proc = PendingParseTracker(root)
    download_proc = PendingParseTracker(root)

    # parse successfully handles two of the three games; the third fails
    # and should remain pending
    parse_proc.mark_parsed(date, {'020451', '020452'})

    # meanwhile a concurrent download run detects one more changed game
    # and saves before parse does
    download_proc.mark_changed(date, {'020454'})
    download_proc.save()

    # parse finishes afterwards and saves its own (older) view
    parse_proc.save()

    final = PendingParseTracker(root)
    assert final.get_pending(date) == {'020453', '020454'}
