#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re

import requests
from lxml import html

from db import commit_db_item
from db.team import Team
from db.player import Player
from db.player_draft import PlayerDraft

logger = logging.getLogger(__name__)


class PlayerDraftRetriever():

    NHL_PLAYER_DRAFT_PREFIX = "https://www.nhl.com/player"
    DRAFT_INFO_REGEX = re.compile(R"(\d{4})\s(.+),\s(\d+).+\srd,.+\((\d+).+\soverall\)")

    def __init__(self):
        pass

    def retrieve_draft_information(self, player_id):
        """
        Retrieves draft information for player with specified id.
        """
        plr = Player.find_by_id(player_id)
        logger.info("+ Retrieving draft information for %s" % plr.name)

        raw_draft_info = self.retrieve_raw_draft_data(player_id)

        if raw_draft_info is None:
            logger.info("+ No draft information retrievable for %s" % plr.name)
            return

        logger.debug(
            "+ Raw draft information for %s: %s" % (plr.name, raw_draft_info))

        match = re.search(self.DRAFT_INFO_REGEX, raw_draft_info)
        if match:
            dft_year = int(match.group(1))
            dft_team = Team.find_by_abbr(match.group(2))
            dft_round = int(match.group(3))
            dft_overall = int(match.group(4))

            draft_info_db = PlayerDraft.find(
                player_id, dft_team.team_id, dft_year)

            if draft_info_db:
                logger.info(
                    "+ Draft information for %s already in database" % (
                        plr.name))
                return

            draft_info = PlayerDraft(
                player_id, dft_team.team_id, dft_year, dft_round, dft_overall)

            commit_db_item(draft_info)

        else:
            logger.info(
                "+ No draft information for %s decodable from %s" % (
                    plr.name, raw_draft_info))

    def retrieve_raw_draft_data(self, player_id):
        """
        Retrieves raw draft information from profile page of
        player with specified id.
        """
        url = "/".join((self.NHL_PLAYER_DRAFT_PREFIX, str(player_id)))
        r = requests.get(url)
        doc = html.fromstring(r.text)

        raw_draft_info = doc.xpath(
            "//li[@class='player-bio__item']/span[text() = " +
            "'Draft:']/parent::li/text()")

        if not raw_draft_info:
            return
        else:
            return raw_draft_info.pop()
