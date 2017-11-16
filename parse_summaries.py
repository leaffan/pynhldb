#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from parsers.main_parser import MainParser


if __name__ == '__main__':

    src = R"D:\nhl\official_and_json\_2015-16\2016-04\2016-04-10.zip"
    # overtime game [021119]
    src = R"D:\nhl\official_and_json\2016-17\2017-03\2017-03-26.zip"
    # shootout games [021194, 021214, 021216, 021177]
    src = R"D:\nhl\official_and_json\2016-17\2017-04\2017-04-06.zip"
    src = R"D:\nhl\official_and_json\2016-17\2017-04\2017-04-03.zip"
    # simultaneous blocks
    src = R"D:\nhl\official_and_json\_2015-16\2015-10\2015-10-14.zip"
    tgt_game_id = '020047'
    # simultaneous hits
    src = R"D:\nhl\official_and_json\_2015-16\2015-10\2015-10-10.zip"
    tgt_game_id = '020030'
    # simultaneous faceoffs??
    # simultaneous giveaways
    src = R"D:\nhl\official_and_json\_2015-16\2015-10\2015-10-08.zip"
    tgt_game_id = '020007'
    # simultaneous goals + misses in shootout
    # ...

    src = R"D:\nhl\official_and_json\2017-18\2017-11\2017-11-15.zip"
    tgt_game_ids = ['020200']

    src = R"D:\nhl\official_and_json\2017-18\2017-10"

    if os.path.isfile(src):
        data_src = [src]
    elif os.path.isdir(src):
        data_src = [os.path.join(src, f) for f in os.listdir(src)]

    for f in data_src[:]:
        if not os.path.splitext(f)[-1].lower().endswith(".zip"):
            continue
        print("+ Using data source '%s'" % f)

        # mp = MainParser(src, tgt_game_ids)
        mp = MainParser(f)

        # mp.parse_games_sequentially()
        mp.parse_games_simultaneously()

        mp.dispose()
