#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import itertools
import tempfile
from zipfile import ZipFile

from utils.summary_downloader import SummaryDownloader


def test_download_unzipped():

    date = "Oct 24, 2016"
    tgt_dir = tempfile.mkdtemp(prefix='sdl_test_')
    prefixes = ["ES", "FC", "GS", "PL", "RO", "SS", "TH", "TV"]
    game_ids = ["020081", "020082"]

    # setting up list of all HTML report files that should be downloaded for
    # specified date
    files = ["".join(c) + ".HTM" for c in list(
        itertools.product(prefixes, game_ids))]
    # adding JSON game report files
    files.extend(["".join((gid, ".json")) for gid in game_ids])
    # adding shootout report for one of the games
    files.append("SO020082.HTM")

    sdl = SummaryDownloader(tgt_dir, date, zip_summaries=False)
    sdl.run()
    tgt_dir = sdl.get_tgt_dir()

    assert sorted(os.listdir(tgt_dir)) == sorted(files)


def test_download_zipped():

    date = "Oct 24, 2016"
    tgt_dir = tempfile.mkdtemp(prefix='sdl_test_')
    prefixes = ["ES", "FC", "GS", "PL", "RO", "SS", "TH", "TV"]
    game_ids = ["020081", "020082"]

    # setting up list of all HTML report files that should be downloaded for
    # specified date
    files = ["".join(c) + ".HTM" for c in list(
        itertools.product(prefixes, game_ids))]
    # adding JSON game report files
    files.extend(["".join((gid, ".json")) for gid in game_ids])
    # adding shootout report for one of the games
    files.append("SO020082.HTM")

    sdl = SummaryDownloader(tgt_dir, date)
    sdl.run()
    zip_path = sdl.get_zip_path()

    zip = ZipFile(zip_path)

    assert sorted(zip.namelist()) == sorted(files)
