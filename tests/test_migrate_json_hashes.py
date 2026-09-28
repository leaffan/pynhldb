#!/usr/bin/env python

import hashlib
import json
import os
from zipfile import ZipFile

import migrate_json_hashes
from utils.summary_downloader import hashable_json_string


def test_url_to_json_filename():

    feed_url = "https://api-web.nhle.com/v1/gamecenter/2025020016/play-by-play"
    sc_url = "https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=2025020016"
    html_url = "http://www.nhl.com/scores/htmlreports/20252026/GS020016.HTM"

    assert migrate_json_hashes.url_to_json_filename(feed_url) == "020016.json"
    assert migrate_json_hashes.url_to_json_filename(sc_url) == "020016_sc.json"
    assert migrate_json_hashes.url_to_json_filename(html_url) is None


def test_migrate_rewrites_json_hashes_and_leaves_html_untouched(tmpdir):

    base_tgt_dir = tmpdir.mkdir('2025-26').strpath
    month_dir = os.path.join(base_tgt_dir, '2025-10')
    os.makedirs(month_dir)

    full_game_id = '2025020016'
    game_id = full_game_id[-6:]

    game_feed_content = {
        'plays': [{'details': {'zoneCode': 'D'}}],
        'rosterSpots': [
            {'playerId': 1, 'firstName': {'default': 'Matthew'}, 'lastName': {'default': 'Lundestrom'}},
        ],
    }
    shift_chart_content = {
        'data': [{'playerId': 1, 'firstName': 'Matthew', 'lastName': 'Lundestrom'}],
    }

    # old-style hashes: computed on the full content (including names),
    # exactly how the pre-fix code used to do it
    old_feed_hash = hashlib.md5(json.dumps(game_feed_content).encode('utf-8')).hexdigest()
    old_sc_hash = hashlib.md5(json.dumps(shift_chart_content).encode('utf-8')).hexdigest()

    feed_url = f"https://api-web.nhle.com/v1/gamecenter/{full_game_id}/play-by-play"
    sc_url = f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={full_game_id}"
    html_url = "http://www.nhl.com/scores/htmlreports/20252026/GS020016.HTM"

    mod_timestamps = {
        feed_url: old_feed_hash,
        sc_url: old_sc_hash,
        # an unrelated HTML report url, should be left untouched
        html_url: "Wed, 08 Oct 2025 23:00:00 GMT",
    }
    mts_path = os.path.join(base_tgt_dir, '_mod_timestamps.json')
    with open(mts_path, 'w') as f:
        json.dump(mod_timestamps, f, indent=2, sort_keys=True)

    # zip up the two raw JSON files, like the real downloader does
    zip_path = os.path.join(month_dir, '2025-10-09.zip')
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr(f"{game_id}.json", json.dumps(game_feed_content, indent=2))
        zf.writestr(f"{game_id}_sc.json", json.dumps(shift_chart_content, indent=2))

    migrate_json_hashes.migrate(mts_path)

    with open(mts_path) as f:
        migrated = json.load(f)

    assert migrated[feed_url] == hashlib.md5(hashable_json_string(game_feed_content).encode('utf-8')).hexdigest()
    assert migrated[sc_url] == hashlib.md5(hashable_json_string(shift_chart_content).encode('utf-8')).hexdigest()
    assert migrated[html_url] == "Wed, 08 Oct 2025 23:00:00 GMT"


def test_migrate_handles_missing_local_files_gracefully(tmpdir):

    base_tgt_dir = tmpdir.mkdir('2025-26').strpath

    feed_url = "https://api-web.nhle.com/v1/gamecenter/2025020099/play-by-play"
    mod_timestamps = {feed_url: "some-old-hash"}
    mts_path = os.path.join(base_tgt_dir, '_mod_timestamps.json')
    with open(mts_path, 'w') as f:
        json.dump(mod_timestamps, f, indent=2, sort_keys=True)

    # no zip/loose file exists for this game - migrate() should leave the
    # stored hash untouched rather than raising
    migrate_json_hashes.migrate(mts_path)

    with open(mts_path) as f:
        migrated = json.load(f)

    assert migrated[feed_url] == "some-old-hash"
