#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from operator import sub

from utils import str_to_timedelta

logger = logging.getLogger(__name__)


class GoalieParser():

    WIN_LOSS_REGEX = re.compile("\((W|L|T|OT)\)")

    GOALIE_GAME_ATTRS = [
        'win', 'loss', 'tie', 'regulation_tie',
        'overtime_game', 'shootout_game',
        'shutout', 'en_goals', 'otl']

    def __init__(self, raw_data, raw_so_data=None):
        self.raw_data = raw_data
        self.raw_so_data = raw_so_data
        self.goalie_data = dict()
        self.goalies = dict()

    def create_goalies(self, game, rosters):
        self.game = game
        self.rosters = rosters
        self.load_data()

        for key in ['road', 'home']:
            if key == 'road':
                team_id = self.game.road_team_id
            else:
                team_id = self.game.home_team_id

            goalies_in_game = self.retrieve_goalies_in_game(
                self.goalie_data[key])

            for goalie_data_tr in goalies_in_game:
                tokens = goalie_data_tr.xpath("td/text()")

                goalie_game_data_dict = dict()

                for item in self.GOALIE_GAME_ATTRS:
                    goalie_game_data_dict[item] = 0

                    goalie_game_data_dict['no'] = int(tokens[0])
                    plr_game = self.rosters[key][goalie_game_data_dict['no']]

                    goalie_game_data_dict = self.retrieve_time_on_ice(
                        goalie_game_data_dict, tokens)

                    goalie_game_data_dict = self.retrieve_goals_shots_against(
                        goalie_game_data_dict, tokens)

                    goalie_game_data_dict = self.retrieve_win_loss_situation(
                        goalie_game_data_dict, tokens)

            for p in sorted(goalie_game_data_dict.keys()):
                print("\t", p, goalie_game_data_dict[p])

            print(team_id, plr_game)

    def retrieve_win_loss_situation(self, data_dict, tokens):
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
