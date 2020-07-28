#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
from urllib.parse import urlparse

import requests
from lxml import html

from db import commit_db_item
from db.player import Player
from db.team import Team
from utils import retrieve_season

logger = logging.getLogger(__name__)


class PlayerFinder():
    # url components to retrieve current player rosters
    NHL_SITE_PREFIX = "https://www.nhl.com"
    # stats api prefix
    API_SITE_PREFIX = "https://statsapi.web.nhl.com/api/v1"
    NHL_SITE_ROSTER_SUFFIX = "roster"
    # url components to retrieve current in-the-system player information
    TEAM_SITE_PREFIX = "http://%s.nhl.com"
    TEAM_SITE_ROSTER_SUFFIX = "/club/roster.htm?type=prospect"
    # url components to retrieve information about currently contracted players
    CAPFRIENDLY_SITE_PREFIX = "https://www.capfriendly.com/teams/"
    # url prefix for json structure with team information
    API_TEAM_SITE_PREFIX = '/'.join((API_SITE_PREFIX, 'teams/'))
    # url prefix for json structure with player information
    PEOPLE_SITE_PREFIX = '/'.join((API_SITE_PREFIX, 'people/'))
    # url components for json structure with player name search suggestions
    SUGGEST_SITE_PREFIX = (
        "http://suggest.svc.nhl.com/svc/suggest/v1/minplayers/")
    # maximum number of suggestions
    SUGGEST_SITE_SUFFIX = "/99999"

    def __init__(self):
        pass

    def find_players_for_team(self, team, src='roster', season=None):
        """
        Finds players currently on roster/in system for specified team.
        """
        # creating class wide variable to hold current team
        if type(team) is str:
            team = Team.find(team)

        print("+ Searching %s players for %s" % (src, team))

        if src == 'roster':
            players = self.get_roster_players_via_api(team, season)
        elif src == 'system':
            players = self.get_system_players(team)
        elif src == 'contract':
            players = self.get_contracted_players(team)

        return players

    def get_roster_players_via_api(self, team, season=None):
        """
        Retrieves roster players for specified team and season using the NHL
        stats api.
        """
        # setting up empty list of players
        players = list()

        if season is None:
            season = str(retrieve_season())

        # creating stats api url with optional season parameter
        url = "".join((self.API_TEAM_SITE_PREFIX, str(team.team_id)))
        url_params = {
            'expand': 'team.roster',
            'season': "%s%d" % (season, int(season) + 1)
        }
        # retrieving data
        r = requests.get(url, params=url_params)
        team_data = r.json()

        if 'teams' not in team_data:
            logging.warn(
                "+ %s not part of the league in %s/%d" % (
                    team, season, int(season) + 1))
            return players

        team_data = team_data['teams'][0]

        if 'roster' not in team_data:
            logging.warn(
                "+ No roster found for %s/%d %s" % (
                    season, int(season) + 1, team))
            return players

        roster = team_data['roster']['roster']

        for plr_src in roster:
            # retrieving player if of current player in roster
            plr_id = plr_src['person']['id']
            # searching and optionally creating player with found player id
            plr = self.search_player_by_id(plr_id)
            players.append(plr)

        return players

    # previous function to retrieve roster players
    # TODO: deprecate, remove
    def get_roster_players(self, team, season=None):
        """
        Retrieves basic player information from team roster page. Checks
        whether corresponding player already exists in database and creates it
        otherwise.
        """
        # setting up empty list of players
        players = list()

        # getting html document with team's roster
        doc = self.get_html_document(team, 'roster', season)

        # retrieving player page urls, and players' first and last names
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
        # retrieving players' positions
        positions = [x[:1] for x in doc.xpath(
            "//td[@class='position-col fixed-width-font']/text()")]

        for (
            first_name, last_name, url, position
        ) in zip(
            first_names, last_names, urls, positions
        ):
            # retrieving nhl id from player page url
            plr_id = int(url.split("-")[-1])

            # trying to find player in database
            plr = Player.find_by_id(plr_id)
            # creating player if not already in database
            if plr is None:
                plr = self.create_player(
                    plr_id, last_name, first_name, position)
                logging.info("+ %s created" % plr)

            players.append(plr)

        return players

    def get_system_players(self, team):
        """
        Retrieves player data from team's in the system, i.e. prospects, page.
        """
        # setting up empty list of players
        players = list()

        # getting html document with team's prospect system
        doc = self.get_html_document(team, 'system')

        # returning empty list if no system page could be found
        if doc is None:
            return players

        # setting up list with urls to individual player pages
        urls = [
            a for a in doc.xpath(
                    "//tr[contains('rwEven|rwOdd', @class)" +
                    "]/td[2]/nobr/a/@href")]

        for url in urls:
            # retrieving nhl id from player page url
            plr_id = int(urlparse(url).path.split("/")[-1])
            # trying to find player in database
            plr = Player.find_by_id(plr_id)
            # creating player if not already in database
            if plr is None:
                plr = self.search_player_by_id(plr_id)

            players.append(plr)

        return players

    def get_contracted_players(self, team):
        """
        Retrieves player data from team's capfriendly page.
        """
        # setting up empty list of players
        players = list()

        # getting html document with team's contracted players
        doc = self.get_html_document(team, 'contracts')

        # returning empty list if no system page could be found
        if doc is None:
            return players

        # collecting player names and links to capfriendly pages for different
        # player groups
        cf_links = list()
        cf_names = list()
        for group in [
            'FORWARDS', 'DEFENSE', 'GOALIES', 'INJURED'
        ]:
            cf_links += doc.xpath(
                "//table[@id='team']/tbody/tr[@class='column_head c'" +
                "]/td[contains(text(), '%s')]/parent::tr/" % group +
                "following-sibling::tr/td[1]/a/@href")
            cf_names += doc.xpath(
                "//table[@id='team']/tbody/tr[@class='column_head c'" +
                "]/td[contains(text(), '%s')]/parent::tr/" % group +
                "following-sibling::tr/td[1]/a/text()")

        for lnk, name in zip(cf_links, cf_names):
            # retrieving capfriendly id from player page link
            cf_id = lnk.split("/")[-1]
            # trying to find player in database
            plr = Player.find_by_capfriendly_id(cf_id)
            # trying to find player using suggestions
            if plr is None:
                last_name, first_name = name.split(", ")
                suggested_players = self.get_suggested_players(
                    last_name, first_name)
                for suggested_player in suggested_players:
                    (
                        sugg_plr_id, sugg_pos,
                        sugg_last_name, sugg_first_name, _
                    ) = (
                        suggested_player
                    )
                    if (last_name, first_name) == (
                            sugg_last_name, sugg_first_name):
                        plr = Player.find_by_id(sugg_plr_id)
                        if plr is None:
                            plr = self.create_player(
                                sugg_plr_id, last_name, first_name, sugg_pos)

            if plr is None:
                print("Unable to find player with name %s" % name)
            else:
                players.append(plr)

        return players

    def get_roster_players_with_data(self, team):
        # TODO: find usage for this function
        """
        Retrieves player data from team roster page. Checks whether
        corresponding player already exists in database and creates it
        otherwise.
        """
        # getting html document with team's roster
        doc = self.get_html_document(team, 'roster')

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
        weights = [int(x) if x.isdigit() else 0 for x in doc.xpath(
            "//td[@class='weight-col fixed-width-font']/text()")]
        # player dates of birth
        dobs = doc.xpath("//td[@class='birthdate-col']/span[2]/text()")
        hometowns = doc.xpath("//td[@class='hometown-col']/text()")

        players = list()

        for (
            first_name, last_name, url, _, position, _, _, _, _, _
        ) in zip(
            first_names, last_names, urls, numbers, positions,
            hands, weights, heights, dobs, hometowns
        ):
            # retrieving nhl id from player page url
            plr_id = int(url.split("-")[-1])

            # trying to find player in database
            plr = Player.find_by_id(plr_id)
            # creating player if not already in database
            if plr is None:
                plr = self.create_player(
                    plr_id, last_name, first_name, position)
                print("%s created..." % plr)

            players.append(plr)

        return players

    def get_suggested_players(self, last_name, first_name=''):
        """
        Retrieves all players suggested nhl.com after being provided with a
        last name and an optional first name.
        """
        if first_name:
            name = " ".join((first_name, last_name))
        else:
            name = last_name

        url = "".join((
            self.SUGGEST_SITE_PREFIX,
            name.lower(),
            self.SUGGEST_SITE_SUFFIX))
        req = requests.get(url)
        suggestions_json = json.loads(req.text)

        suggested_players = list()

        for suggestion in suggestions_json['suggestions']:
            tokens = suggestion.split("|")
            (sug_id, sug_last_name, sug_first_name, sug_dob, sug_pos) = (
                tokens[0], tokens[1], tokens[2], tokens[10], tokens[12]
            )
            suggested_players.append((
                sug_id, sug_pos, sug_last_name, sug_first_name, sug_dob))

        return suggested_players

    def search_player_by_id(self, plr_id):
        """
        Searches a player in database and on nhl.com using the official id.
        """
        plr = Player.find_by_id(plr_id)

        if plr is None:
            url = "".join((self.PEOPLE_SITE_PREFIX, str(plr_id)))
            req = requests.get(url, params={
                'expand': 'person.stats',
                'stats': 'yearByYear,yearByYearPlayoffs'})
            plr_json = req.json()

            if 'people' in plr_json and len(plr_json['people']):
                person = plr_json['people'][0]

                if all(k in person for k in (
                    'lastName', 'firstName', 'primaryPosition'
                )):
                    last_name = person['lastName']
                    first_name = person['firstName']
                    position = person['primaryPosition']['code']

                    if position == 'N/A':
                        position = None

                    plr = self.create_player(
                        plr_id, last_name, first_name, position)
                    logging.warn("+ %s created" % plr)
                else:
                    logging.warn("+ Insufficient information to create player")
            else:
                logging.warn("+ No player with id %d" % plr_id)

        return plr

    def create_player(
            self, plr_id, last_name, first_name, position,
            alternate_last_names=[], alternate_first_names=[],
            alternate_positions=[], capfriendly_id=None):
        """
        Creates a new player in database using the specified data.
        """
        # initiliazing player object
        # TODO: remove alternate options (if necessary)
        plr = Player(
                plr_id, last_name, first_name, position,
                alternate_last_names=alternate_last_names,
                alternate_first_names=alternate_first_names,
                alternate_positions=alternate_positions)
        if capfriendly_id:
            plr.capfriendly_id = capfriendly_id

        commit_db_item(plr, True)

        return Player.find_by_id(plr_id)

    def get_html_document(self, team, src_type, season=None):
        """
        Gets html data for team roster, in-the-system or capfriendly pages.
        """
        if src_type == 'roster':
            # preparing url to team's roster page
            team_url_component = team.team_name.lower().replace(" ", "")
            # creating url like 'https://www.nhl.com/ducks/roster'
            if season is not None:
                team_url = "/".join((
                    self.NHL_SITE_PREFIX,
                    team_url_component,
                    self.NHL_SITE_ROSTER_SUFFIX,
                    str(season)))
            else:
                team_url = "/".join((
                    self.NHL_SITE_PREFIX,
                    team_url_component,
                    self.NHL_SITE_ROSTER_SUFFIX))
        elif src_type == 'system':
            # preparing url to team's prospects page
            team_url_component = team.team_name.lower().replace(" ", "")
            team_site_prefix = self.TEAM_SITE_PREFIX.replace(
                "%s", team_url_component)
            # creating url like
            # 'http://ducks.ice.nhl.com/club/roster.htm?type=prospect'
            team_url = "".join((
                team_site_prefix,
                self.TEAM_SITE_ROSTER_SUFFIX))
        elif src_type == 'contracts':
            # preparing url to team's prospects page
            team_url_component = team.team_name.lower().replace(" ", "")
            team_url = "".join((
                self.CAPFRIENDLY_SITE_PREFIX, team_url_component))

        try:
            req = requests.get(team_url)
        except requests.exceptions.ConnectionError:
            # TODO: returning empty document tree
            return None
        return html.fromstring(req.text)
