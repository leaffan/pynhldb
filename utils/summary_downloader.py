#!/usr/bin/env python
# -*- coding: utf-8 -*-


class SummaryDownloader():

    # base url for official schedule json page
    SCHEDULE_URL_BASE = "http://statsapi.web.nhl.com/api/v1/schedule"
    # url template for official json gamefeed page 
    JSON_GAME_FEED_URL_TEMPLATE = (
        "http://statsapi.web.nhl.com/api/v1/game/%s/feed/live")
