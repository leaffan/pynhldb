#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from types import StringType

import requests
from lxml import html

from db.player import Player
from db.team import Team

logger = logging.getLogger(__name__)


class PlayerFinder():
    # url prefixes to retrieve current player rosters
    NHL_SITE_PREFIX = "https://www.nhl.com"
    NHL_SITE_ROSTER_SUFFIX = "roster"

    def __init__(self):
        pass

    def find_players_for_team(self, team, src='roster'):
        """
        Finds players currently on roster/in system for specified team.
        """
        # creating class wide variable to hold current team
        if type(team) is StringType:
            team = Team.find(team)
        self.curr_team = team

        print("+ Searching %s players for %s" % (src, team))

        team_url_component = self.curr_team.short_name.lower().replace(" ", "")
        team_url = "/".join((
            self.NHL_SITE_PREFIX,
            team_url_component,
            self.NHL_SITE_ROSTER_SUFFIX))

        if src == 'roster':
            players = self.get_roster_players(team_url)
        elif src == 'system':
            players = self.get_system_players(self.curr_team)

    def get_roster_players(self, url):
        """
        Retrieves player data from team roster page. Checks whether
        corresponding player already exists in database and creates it
        otherwise.
        """
        r = requests.get(url)
        doc = html.fromstring(r.text)

        # retrieving player page urls, and player first and last names
        # from roster page
        urls = doc.xpath("//td[@class='name-col']/a[@href]/@href")
        first_names = doc.xpath(
            "//td[@class='name-col']/a/div/span[@class='name-col__item " +
            "name-col__firstName']/text()")
        # using filter to get rid of empty strings after stripping string 
        # elements
        # using replace to get rid of asterisk indicating players on injury
        # reserve
        last_names = filter(
            None, [
                x.replace("*", "").strip() if x else None for x in doc.xpath(
                    "//td[@class='name-col']/a/div/span[@class='name-" +
                    "col__item name-col__lastName']/text()")])

        # retrieving further player data from roster page
        # player jersey numbers
        numbers = doc.xpath(
            "//td[@class='number-col fixed-width-font']/text()")
        # player positions
        positions = [x[:1] for x in doc.xpath(
            "//td[@class='position-col fixed-width-font']/text()")]
        # shooting hands, unfortunately goaltender's glove hands aren't
        # listed any longer
        hands = doc.xpath("//td[@class='shoots-col fixed-width-font']/text()")
        # player heights (in ft. + in.)
        heights = doc.xpath(
            "//td[@class='height-col fixed-width-font']/span[2]/text()")
        # player weights (in lbs.)
        weights = [int(x) if unicode(x).isdigit() else 0 for x in doc.xpath(
            "//td[@class='weight-col fixed-width-font']/text()")]
        # player dates of birth
        dobs = doc.xpath("//td[@class='birthdate-col']/span[2]/text()")
        hometowns = doc.xpath("//td[@class='hometown-col']/text()")

        players = list()

        for (
            first_name, last_name, url, number, position,
            hand, weight, height, dob, hometown) in zip(
                first_names, last_names, urls, numbers, positions,
                hands, weights, heights, dobs, hometowns):
                    # retrieving nhl id from player page url
                    plr_id = int(url.split("-")[-1])

                    # trying to find player in database
                    plr = Player.find_by_id(plr_id)
                    # creating player if not already in database
                    if plr is None:
                        plr = self.create_player(
                            plr_id, last_name, first_name,
                            position, self.curr_team)

                    players.append(plr)

        return players
