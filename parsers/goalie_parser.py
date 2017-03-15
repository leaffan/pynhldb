#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from operator import sub
from collections import defaultdict

from utils import str_to_timedelta
from db import create_or_update_db_item
from db.goalie_game import GoalieGame

logger = logging.getLogger(__name__)


class GoalieParser():

    # binary goaltender game attributes
    GOALIE_GAME_ATTRS = [
        'win', 'loss', 'tie', 'regulation_tie',
        'overtime_game', 'shootout_game',
        'shutout', 'en_goals', 'otl']
    WIN_LOSS_REGEX = re.compile("\((W|L|T|OT)\)")

    def __init__(self, raw_data, raw_so_data=None):
        self.raw_data = raw_data
        # retrieving raw structured shootout data (if available)
        self.raw_so_data = raw_so_data
        self.goalie_data = dict()
        self.goalies = defaultdict(list)

    def create_goalies(self, game, rosters):
        self.game = game
        self.rosters = rosters
        self.load_data()

        for key in ['road', 'home']:

            team_id = getattr(self.game, "%s_team_id" % key)

            # retrieving goalies actually playing in game
            goalies_in_game = self.retrieve_goalies_in_game(
                self.goalie_data[key])

            for goalie_data_tr in goalies_in_game:
                tokens = goalie_data_tr.xpath("td/text()")

                # setting up goalie game data dictionary
                goalie_game_data_dict = dict()

                # setting several goalie game attributes to default value
                for item in self.GOALIE_GAME_ATTRS:
                    goalie_game_data_dict[item] = 0

                goalie_game_data_dict['no'] = int(tokens[0])
                plr_game = self.rosters[key][goalie_game_data_dict['no']]

                # retrieving goalie's time on ice
                goalie_game_data_dict = self.retrieve_time_on_ice(
                    goalie_game_data_dict, tokens)

                # retrieving shots against, goals against and saves
                goalie_game_data_dict = self.retrieve_goals_shots_against(
                    goalie_game_data_dict, tokens)

                # retrieving win, loss, overtime loss et al.
                goalie_game_data_dict = self.retrieve_win_loss_situation(
                    goalie_game_data_dict, tokens)

                # calculating goals against average, save percentage
                goalie_game_data_dict = self.calculate_gaa_save_pctg(
                    goalie_game_data_dict, tokens, goalies_in_game)

                # retrieving shootout information
                goalie_game_data_dict = self.retrieve_shootout_information(
                    goalie_game_data_dict, plr_game)

                # setting up new goalie game item
                goalie_game = GoalieGame(
                    self.game.game_id, team_id,
                    plr_game.player_id, goalie_game_data_dict)

                # trying to find goalie game item from database
                db_goalie_game = GoalieGame.find(
                    self.game.game_id, plr_game.player_id)

                # creating new or updating existing goalie game item
                create_or_update_db_item(db_goalie_game, goalie_game)

                self.goalies[key].append(
                    GoalieGame.find(self.game.game_id, plr_game.player_id))
        else:
            return self.goalies

    def calculate_gaa_save_pctg(self, data_dict, tokens, goalies_in_game):
        """
        Calculates goals against average and save percentage for current
        goalie in game.
        """
        if data_dict['shots_against']:
            # calculating save percentage
            data_dict['save_pctg'] = round(
                1 - float(data_dict['goals_against']) / float(
                    data_dict['shots_against']), 6)
            # retrieving minutes played
            m, s = tokens[6].split(":")
            dec_min = int(m) + int(s) / 60.
            # calculating goals against average
            data_dict['gaa'] = round(
                data_dict['goals_against'] * 60. / dec_min, 6)
            # registering shutout if applicable
            if data_dict['gaa'] == 0.0 and len(goalies_in_game) == 1:
                data_dict['shutout'] = 1
        else:
            data_dict['save_pctg'] = None
            data_dict['gaa'] = None
        return data_dict

    def retrieve_shootout_information(self, data_dict, plr_game):
        """
        Retrieves shootout information for current goalie in game.
        """
        if self.raw_so_data is None:
            return data_dict
        # retrieving all goalies participating in the shootout
        so_goalies = set(
            self.raw_so_data.xpath(
                "//td[@class='sectionheading' and contains(text(), " +
                "'Shootout Order')]/parent::tr/following-sibling::tr" +
                "/td/table/tr[@height='30']/td[5]/text()"))
        if len(so_goalies) < 2:
            logger.warn(
                "Unable to retrieve goalies participating in" +
                "shootout: %s" % str(so_goalies))
        for so_goalie in so_goalies:
            # retrieving shootout goalie's number and name
            try:
                so_no, so_name = so_goalie.split()
            except:
                logger.warn(
                    "Unable to retrieve shootout goalie number" +
                    "and name from %s" % so_goalie)
                continue
            so_name = so_name.split(".")
            if int(so_no) == data_dict['no']:
                goalie_last_name = plr_game.get_player().last_name.upper()
                if so_name[-1] == goalie_last_name:
                    data_dict['shootout_game'] = 1
                    break
        return data_dict

    def retrieve_win_loss_situation(self, data_dict, tokens):
        """
        Retrieves win, losses et al. for current goalie in game.
        """
        if re.search(self.WIN_LOSS_REGEX, tokens[2]) is not None:
            win_loss = re.search(
                self.WIN_LOSS_REGEX, tokens[2]).group(1)
            if win_loss == 'W':
                data_dict['win'] = 1
                if self.game.overtime_game:
                    data_dict['overtime_game'] = 1
            elif win_loss == 'L':
                data_dict['loss'] = 1
            elif win_loss == 'OT':
                data_dict['otl'] = 1
                data_dict['overtime_game'] = 1
        return data_dict

    def retrieve_goals_shots_against(self, data_dict, tokens):
        """
        Retrieves shots against, goals against and saves for current goalie in
        game.
        """
        try:
            data_dict['goals_against'], data_dict['shots_against'] = tuple(
                [int(x.strip()) for x in tokens[-1].split("-")])
        except ValueError:
            data_dict['goals_against'] = 0
            data_dict['shots_against'] = 0
        finally:
            data_dict['saves'] = sub(
                data_dict['shots_against'],
                data_dict['goals_against'])
        return data_dict

    def retrieve_time_on_ice(self, data_dict, tokens):
        """
        Retrieves time-on-ice for current goalie in game.
        """
        data_dict['toi_overall'] = str_to_timedelta(tokens[6])
        data_dict['toi_pp'] = str_to_timedelta(tokens[4])
        data_dict['toi_sh'] = str_to_timedelta(tokens[5])
        data_dict['toi_ev'] = str_to_timedelta(tokens[3])
        return data_dict

    def retrieve_goalies_in_game(self, goalie_data_trs):
        """
        From all goalies listed in specified table rows selects and returns
        only those that actually played in the current game.
        """
        goalies_in_game = list()

        for goalie_data_tr in goalie_data_trs:
            tokens = goalie_data_tr.xpath("td/text()")
            # bailing out if current goaltender didn't play, i.e. has no
            # icetime (mm:ss) registered but a blank string
            if ":" not in tokens[6]:
                continue
            # sometimes goalies that didn't play have "00:00" as total ice-
            # time, e.g. Chris Osgood in Game 129 in 2007/08
            if set([int(item) for item in tokens[6].split(":")]) == set([0]):
                continue
            goalies_in_game.append(goalie_data_tr)

        return goalies_in_game

    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        # finding nested table cell headlining current game's goalie summary
        goalie_summary_td = self.raw_data.xpath(
            "//td[contains(text(), 'GOALTENDER SUMMARY')]")[0]
        # retrieving all table rows with any kind of goalie information
        all_goalie_trs = goalie_summary_td.xpath(
            "parent::tr/following-sibling::tr//tr[" +
            "@class='evenColor' or @class='oddColor']")
        # retrieving table cell headlining current game's home goalie summary
        home_goalie_summary_td = goalie_summary_td.xpath(
            "parent::tr/following-sibling::tr//table/tr/td[" +
            "contains(@class, 'homesectionheading') and @rowspan='2']")[0]
        # retrieving all table row with home goalie information
        home_goalie_trs = home_goalie_summary_td.xpath(
            "parent::tr/following-sibling::tr[" +
            "@class='evenColor' or @class='oddColor']")

        # retrieving all table rows with road goalie information by
        # differentiating home goalie information from complete goalie
        # information
        road_goalie_trs = list(
            set(all_goalie_trs).difference(set(home_goalie_trs)))

        self.goalie_data['road'] = road_goalie_trs
        self.goalie_data['home'] = home_goalie_trs
