#!/usr/bin/env python

import logging
import re

import requests

from db import commit_db_item
from db.player import Player
from db.player_draft import PlayerDraft
from db.team import Team

logger = logging.getLogger(__name__)


class PlayerDraftRetriever:

    NHL_PLAYER_DRAFT_PREFIX = "https://www.nhl.com/player"
    DRAFT_INFO_REGEX = re.compile(R"(\d{4})\s(.+),\s(\d+).+\srd,.+\((\d+).+\soverall\)")

    def __init__(self):
        pass

    def retrieve_draft_information(self, player_id):
        """
        Retrieves draft information for player with specified id.
        """
        plr = Player.find_by_id(player_id)
        logger.info(f"+ Retrieving draft information for {plr.name}")

        raw_draft_info = self.retrieve_raw_draft_data(player_id)

        if raw_draft_info is None:
            logger.info(f"+ No draft information retrievable for {plr.name}")
            return

        logger.debug(
            f"+ Raw draft information for {plr.name}: {raw_draft_info}")

        dft_year = int(raw_draft_info.get("year"))
        dft_team = Team.find_by_abbr(raw_draft_info.get("teamAbbrev"))
        dft_round = int(raw_draft_info.get("round"))
        dft_overall = int(raw_draft_info.get("overallPick"))

        draft_info_db = PlayerDraft.find(
            player_id, dft_team.team_id, dft_year)

        if draft_info_db:
            logger.info(
                f"+ Draft information for {plr.name} already in database")
            return

        draft_info = PlayerDraft(
            player_id, dft_team.team_id, dft_year, dft_round, dft_overall)

        commit_db_item(draft_info)


    def retrieve_raw_draft_data(self, player_id):
        """
        Retrieves raw draft information from profile page of
        player with specified id.
        """
        url = f"https://api-web.nhle.com/v2/player/{player_id}/bio"
        r = requests.get(url)
        bio = r.json()

        raw_draft_info = bio.get("draftDetails")

        if not raw_draft_info:
            return
        else:
            return raw_draft_info
