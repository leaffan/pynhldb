#!/usr/bin/env python

import itertools
import os
from zipfile import ZipFile

from utils.summary_downloader import SummaryDownloader, hashable_json_string


def test_download_unzipped(tmpdir):

    date, files = set_up_comparison_files()

    sdl = SummaryDownloader(tmpdir.mkdir('sdl').strpath, date, zip_summaries=False)
    sdl.run()
    tgt_dir = sdl.get_tgt_dir()

    assert sorted(os.listdir(tgt_dir)) == sorted(files)

    # deactivated due to performance reasons
    # tmpdir.remove()


def test_download_zipped(tmpdir):

    date, files = set_up_comparison_files()

    sdl = SummaryDownloader(tmpdir.mkdir('sdl').strpath, date, cleanup=False)
    sdl.run()
    zip_path = sdl.get_zip_path()

    zip_file = ZipFile(zip_path)

    assert sorted(zip_file.namelist()) == sorted(files)

    zip_file.close()

    # deactivated due to performance reasons
    # tmpdir.remove()


def test_hashable_json_string_ignores_cosmetic_name_changes():

    game_feed_data = {
        'plays': [{'details': {'zoneCode': 'D'}}],
        'rosterSpots': [
            {'playerId': 1, 'firstName': {'default': 'Matthew'}, 'lastName': {'default': 'Lundestrom'}},
        ],
    }
    renamed_game_feed_data = {
        'plays': [{'details': {'zoneCode': 'D'}}],
        'rosterSpots': [
            {'playerId': 1, 'firstName': {'default': 'Matt'}, 'lastName': {'default': 'Lundestrom'}},
        ],
    }

    assert hashable_json_string(game_feed_data) == hashable_json_string(renamed_game_feed_data)

    shift_chart_data = {'data': [{'playerId': 1, 'firstName': 'Matthew', 'lastName': 'Lundestrom'}]}
    renamed_shift_chart_data = {'data': [{'playerId': 1, 'firstName': 'Matt', 'lastName': 'Lundestrom'}]}

    assert hashable_json_string(shift_chart_data) == hashable_json_string(renamed_shift_chart_data)


def test_hashable_json_string_still_detects_real_changes():

    original = {'plays': [{'details': {'zoneCode': 'D'}}], 'rosterSpots': []}
    corrected = {'plays': [{'details': {'zoneCode': 'O'}}], 'rosterSpots': []}

    assert hashable_json_string(original) != hashable_json_string(corrected)


def test_hashable_json_string_does_not_mutate_input():

    game_feed_data = {
        'rosterSpots': [{'playerId': 1, 'firstName': 'Matthew', 'lastName': 'Lundestrom'}],
    }

    hashable_json_string(game_feed_data)

    assert game_feed_data['rosterSpots'][0]['firstName'] == 'Matthew'
    assert game_feed_data['rosterSpots'][0]['lastName'] == 'Lundestrom'


def set_up_comparison_files():

    date = "Oct 24, 2016"
    prefixes = ["ES", "FC", "GS", "PL", "RO", "SS", "TH", "TV"]
    game_ids = ["020081", "020082"]

    # setting up list of all HTML report files that should be downloaded for
    # specified date
    files = ["".join(c) + ".HTM" for c in list(itertools.product(prefixes, game_ids))]
    # adding JSON game feed files
    files.extend([f"{gid}.json" for gid in game_ids])
    # adding JSON shift chart files
    files.extend([f"{gid}_sc.json" for gid in game_ids])
    # adding shootout report for one of the games
    files.append("SO020082.HTM")

    return date, files
