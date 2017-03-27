#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from parsers.main_parser import MainParser


if __name__ == '__main__':

    src = r"D:\nhl\official_and_json\2016-17\2017-02\2017-02-01.zip"
    # src = r"D:\nhl\official_and_json\2016-17\2017-02\2017-02-20"
    # src = r"D:\nhl\official_and_json\_2015-16\2016-05\2016-05-09.zip"

    src_dir = r"D:\nhl\official_and_json\_2014-15\2014-12"
    src_dir = r"D:\nhl\official_and_json\2016-17\2016-10"
    src_dir = r"D:\nhl\official_and_json\_2015-16\2016-04"

    files = os.listdir(src_dir)
    files = [src]

    # for f in files[17:18]:
    for f in files[:1]:
        print(f)
        if not os.path.splitext(f)[-1].lower().endswith(".zip"):
            continue
        src = os.path.join(src_dir, f)
        mp = MainParser(src)
        print(mp.game_ids)

        for game_id in mp.game_ids[:1]:
            mp.parse_single_game(game_id)

