#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from collections import defaultdict

from utils import str_to_timedelta, player_finder
from db import create_or_update_db_item
from db.player import Player
from db.player_game import PlayerGame

logger = logging.getLogger(__name__)


class RosterParser():

    # event summary values and statistics for each player in roster in
    # exact the same order as in the original html table row
    PLAYER_GAME_ATTRS = [
        "no", "position", "name", "goals", "assists", "points", "plus_minus",
        "penalties", "pim", "toi_overall", "no_shifts", "avg_shift", "toi_pp",
        "toi_sh", "toi_ev", "shots_on_goal", "shots_blocked", "shots_missed",
        "hits", "giveaways", "takeaways", "blocks",
        "faceoffs_won", "faceoffs_lost",
    ]

    def __init__(self, raw_data):
        # receiving structured raw data
        self.raw_data = raw_data
        # setting up dictionary for event summary data (from parsed document)
        self.event_summary = dict()
        # setting up dictionary for roster data
        self.roster_data = defaultdict(dict)
        # setting up final dictionary for team rosters
        self.rosters = dict()

    def create_roster(self, game, teams, raw_roster_report):
        """
        Retrieves player rosters (event summary per player, starting lineup,
        captaincy roles) for specified game and teams.
        """
        # loading and pre-processing structured raw data
        self.load_data()

        self.retrieve_starting_lineup_captains(raw_roster_report)

        for key in sorted(self.event_summary.keys(), reverse=True):
            curr_team = teams[key]
            self.rosters[key] = dict()
            for summary_item in self.event_summary[key]:
                plr_id = summary_item['plr_id']

                # setting role as captain/alternate captain
                if summary_item['no'] == self.roster_data[key]['captain']:
                    summary_item['captain'] = True
                elif summary_item['no'] in self.roster_data[key][
                        'alternate_captains']:
                    summary_item['alternate_captain'] = True
                # setting position in starting lineup
                if summary_item['no'] in self.roster_data[key]['starting']:
                    summary_item['starting'] = True

                # setting up new player game item
                plr = Player.find_by_id(plr_id)
                if not plr:
                    plr = player_finder.PlayerFinder().search_player_by_id(plr_id)
                    logging.info(f"{plr} created")

                new_pgame = PlayerGame(
                    game.game_id, curr_team.team_id, plr_id, summary_item)

                # trying to find existing player game item in database
                db_pgame = PlayerGame.find(
                    new_pgame.game_id, new_pgame.player_id)
                # updating existing or creating new player game item
                create_or_update_db_item(db_pgame, new_pgame)
                # adding player game item to team roster dictionary for current
                # game using jersey number as key
                self.rosters[key][new_pgame.no] = PlayerGame.find(
                    new_pgame.game_id, new_pgame.player_id)
        else:
            return self.rosters

    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        # retrieving all table row elements that are located either above or
        # below a table row that spans the whole table width and separates
        # road and home team rosters
        for key, element_pos in (['road', 'preceding'], ['home', 'following']):
            self.event_summary[key] = self.raw_data.xpath(
                "//tr/td[@colspan='25' or @colspan='22']/parent::*/" +
                "%s-sibling::*" % element_pos)

        # transforming table row elements into lists of data
        for key in ['road', 'home']:

            event_summary = list()

            trs = self.event_summary[key]
            # retaining only those rows that have a number in their first table
            # cell, i.e. represent a player
            trs = [tr for tr in trs if tr.xpath("td/text()")[0].isnumeric()]
            # retaining only those rows that contain more cells than a certain
            # threshold, thereby eliminating additional rows for goalies
            trs = [tr for tr in trs if len(tr) > 15]
            # retrieving text contents
            contents = [tr.xpath("td/text()") for tr in trs]
            # replacing null strings with zeros
            contents = [[
                s.replace('\xa0', '0') for s in item] for item in contents]

            # creating data dictionaries for each table row, e.g. player
            for tr, content in zip(trs, contents):
                content = [c for c in content if c.strip()]
                single_event_summary_item = dict()
                # adding player id to single roster line
                single_event_summary_item['plr_id'] = int(
                    tr.xpath("td/span/@nhl_id")[0])
                # retrieving values from table row contents
                for attr in self.PLAYER_GAME_ATTRS:
                    val = content[self.PLAYER_GAME_ATTRS.index(attr)]
                    # converting time-on-ice data and average shift length
                    # to timedelta intervals
                    if attr.startswith('toi') or attr.startswith('avg'):
                        val = str_to_timedelta(val)
                    # leaving position and name unchanged
                    elif attr in ['position', 'name']:
                        pass
                    # converting everything else into integers
                    else:
                        val = int(val)

                    single_event_summary_item[attr] = val
                # adding single roster line to all roster lines
                event_summary.append(single_event_summary_item)
            # setting roster data for current team type to retrieved contents
            self.event_summary[key] = event_summary

    def retrieve_starting_lineup_captains(self, raw_ro_data):
        """
        Retrieves players serving as (alternate) captain(s) and as part of the
        starting lineup.
        """
        # retrieving rosters for road and home team from corresponding summary
        self.roster_data['road']['raw'], self.roster_data['home']['raw'] = (
            raw_ro_data.xpath(
                "//table[@align='center' and  @width='100%' and " +
                "@cellspacing = '0' and @border = '0']")[1:3])

        for key in self.roster_data.keys():
            # retrieving raw captain and alternate captains
            captains = self.roster_data[key]['raw'].xpath(
                "tr/td[contains(@class, 'italic')]/text()")
            # setting initial values for captaincy roles
            self.roster_data[key]['alternate_captains'] = list()
            self.roster_data[key]['captain'] = None
            # retrieving actual players (via numbers) for captaincy roles
            for no, pos, name in [
                    captains[x:x+3] for x in range(0, len(captains), 3)]:
                if name.strip().endswith('(C)'):
                    self.roster_data[key]['captain'] = int(no)
                elif name.strip().endswith('(A)'):
                    self.roster_data[key]['alternate_captains'].append(int(no))
            # retrieving raw starting lineup
            starting_lineup = self.roster_data[key]['raw'].xpath(
                "tr/td[contains(@class, 'bold')]/text()")
            # retrieving actual players (via numbers) in starting lineup
            self.roster_data[key]['starting'] = [
                int(x) for x in starting_lineup[::3]]
