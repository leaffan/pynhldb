#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

import requests
from lxml import html

from db.team import Team
from db.player_draft import PlayerDraft

class PlayerDraftRetriever():

    NHL_PLAYER_DRAFT_PREFIX = "https://www.nhl.com/player"
    DRAFT_INFO_REGEX = re.compile(
        "(\d{4})\s(.+),\s(\d+).+\srd,.+\((\d+).+\soverall\)")

    def __init__(self):
        pass

    def retrieve_draft_information(self, player_id):

        url = "/".join((self.NHL_PLAYER_DRAFT_PREFIX, str(player_id)))
        r = requests.get(url)
        doc = html.fromstring(r.text)

        raw_draft_info = doc.xpath(
            "//li[@class='player-bio__item']/span[text() = " +
            "'Draft:']/parent::li/text()")

        if not raw_draft_info:
            print("No draft information found")
            return

        raw_draft_info = raw_draft_info.pop()
        print(raw_draft_info)

        match = re.search(self.DRAFT_INFO_REGEX, raw_draft_info)
        if match:
            year = int(match.group(1))
            team = Team.find_by_orig_abbr(match.group(2))
            round = int(match.group(3))
            overall = int(match.group(4))
            draft_info = PlayerDraft(
                player_id, team.team_id, year, round, overall)

            draft_info_db = PlayerDraft.find_by_player_id(player_id)

            if draft_info_db:
                if draft_info_db != draft_info:
                    draft_info_db.update(draft_info)
