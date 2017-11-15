#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime, time, timedelta

from dateutil import parser

from db import create_or_update_db_item
from db.common import session_scope
from db.game import Game
from db.team import Team
from db.team_game import TeamGame
from utils import (
    remove_null_strings, retrieve_season, str_to_timedelta, ordinal)

logger = logging.getLogger(__name__)


class GameParser():

    # time zone names and offsets (in seconds)
    TZINFO = {'CET':   3600, 'CEST': 7200,
              'EET':   7200, 'EETDST': 10800,
              'EDT': -14400, 'EST': -18000,
              'CDT': -18000, 'CST': -21600,
              'MDT': -21600, 'MST': -25200,
              'PDT': -25200, 'PST': -28800,
              'BST':   3600}

    # regular expression to retrieve attendance figure
    ATTENDANCE_AT_VENUE_REGEX = re.compile("\s(@|at)\s")

    # retrieving per period ordinal strings
    PER_PERIOD_ORDINALS = [ordinal(i) for i in range(1, 4)]

    def __init__(self, game_id, raw_data, raw_so_data=None):
        self.game_id = game_id
        self.raw_data = raw_data
        self.raw_so_data = raw_so_data

    def create_game(self, teams):
        # loading and pre-processing raw data
        self.load_data()
        game_data = dict()

        # retrieving standard game information
        game_data = self.retrieve_standard_game_data(game_data)
        # retrieving game attendance and venue
        (
            game_data['attendance'],
            game_data['venue']) = self.retrieve_game_attendance_venue()
        # retrieving game start and end time
        game_data['start'], game_data['end'] = self.retrieve_game_start_end(
            game_data['date'], game_data['type'])
        # retrieving information whether game ended in overtime and/or shootout
        (
            game_data['overtime_game'],
            game_data['shootout_game']
        ) = self.retrieve_overtime_shootout_information(game_data['type'])

        # retrieving referees
        game_data = self.retrieve_referees(game_data)

        # retrieving informatioan about participating teams
        team_data = self.link_game_with_teams(teams)
        # merging team and game information
        game_data = {**game_data, **team_data}  # noqa: E999

        # trying to find game with same game id in database
        db_game = Game.find_by_id(game_data['game_id'])
        # creating new game
        game = Game(game_data['game_id'], game_data)
        # updating existing or creating new game item in database
        create_or_update_db_item(db_game, game)

        return Game.find_by_id(game.game_id)

    def retrieve_standard_game_data(self, game_data):
        """
        Retrieves basic information for current game, e.g. date, season, type,
        fully qualified id and last modification date of original data.
        """
        # retrieving game date from raw data
        game_data['date'] = parser.parse(self.game_data[0]).date()
        # retrieving season for current game date
        game_data['season'] = retrieve_season(game_data['date'])
        # setting up full game id, corresponding season, game type
        # and partial game id
        game_data['game_id'] = int(
            "%d%s" % (game_data['season'], self.game_id))
        # retrieving game type from partial game id
        game_data['type'] = int(self.game_id[:2])
        # retrieving last modification date of original data
        try:
            game_data['data_last_modified'] = parser.parse(
                self.raw_data.xpath("//p[@id='last_modified']/text()")[0])
        except:
            game_data['data_last_modified'] = None

        return game_data

    def retrieve_game_attendance_venue(self):
        """
        Retrieves attendance and venue information for current game.
        """
        # retrieving combined attendance and venue from string,
        # i.e. *Ass./Att. 21,273 @ Centre Bell*
        if any(s in self.game_data[1] for s in ['@', 'at']):
            attendance_venue = self.game_data[1].split(" ", 3)
        else:
            attendance_venue = self.game_data[1].split(" ")

        # trying to convert attendance string into integer value
        try:
            attendance = int(attendance_venue[1].replace(",", ""))
        except:
            logger.warn(
                "+ Unable to convert '%s' to integer" % attendance_venue[1] +
                " attendance value")
            attendance = 0

        # retrieving venue from last element of string split above
        venue = attendance_venue[-1]

        return attendance, venue

    def retrieve_game_start_end(self, game_date, game_type):
        """
        Retrieves start and end timestamp for current game.
        """
        # retrieving start and end time strings from original data,
        # e.g. *Debut/Start 7:46 EDT; Fin/End 10:03 EDT*
        start_end = self.game_data[2].split(";")

        # retrieving raw start time and time zone
        start_time, start_timezone = start_end[0].split()[1:]
        # usually games start after noon
        start_time_suffix = "PM"
        # games may start before noon, but only in the 11th hour
        if int(start_time.split(":")[0]) in [11]:
            start_time_suffix = "AM"
        # turning raw start time, time zone and time suffix into timestamp
        start_time_stamp = parser.parse(
            u" ".join((start_time, start_timezone, start_time_suffix)),
            tzinfos=self.TZINFO)
        # combining game date and time stamp into full start time stamp
        start_date_time_stamp = datetime.combine(
            game_date, time(
                start_time_stamp.hour, start_time_stamp.minute,
                start_time_stamp.second, start_time_stamp.microsecond,
                start_time_stamp.tzinfo))

        # retrieving raw end time and time zone
        end_time, end_timezone = start_end[1].split()[1:]
        # usually games end after noon on the same day they started
        end_time_suffix = "PM"
        end_date = game_date
        # only playoff games may end after midnight
        if int(start_time.split(":")[0]) != 12:
            if int(end_time.split(":")[0]) < int(start_time.split(":")[0]):
                if game_type == 3:
                    print(start_end)
                    end_time_suffix = "AM"
                    end_date = game_date + timedelta(days=1)

        # turning raw end time, time zone and time suffix into timestamp
        end_time_stamp = parser.parse(
            u" ".join((end_time, end_timezone, end_time_suffix)),
            tzinfos=self.TZINFO)
        # combining game date and time stamp into full end time stamp
        end_date_time_stamp = datetime.combine(
            end_date, time(
                end_time_stamp.hour, end_time_stamp.minute,
                end_time_stamp.second, end_time_stamp.microsecond,
                end_time_stamp.tzinfo))

        return start_date_time_stamp, end_date_time_stamp

    def retrieve_overtime_shootout_information(self, game_type):
        """
        Retrieves information whether current game ended in overtime or a
        shootout.
        """
        overtime_game = False
        shootout_game = False

        # retrieving all scoring summary table rows from original html data
        scoring_trs = self.raw_data.xpath(
            "//td[contains(text(), 'SCORING SUMMARY')]/ancestor::tr/" +
            "following-sibling::tr[1]/td/table/tr[contains(@class, 'Color')]")

        # retrieving all table cells with periods a goal was scored in
        score_periods_tds = [tr.xpath("td[2]/text()")[0] for tr in scoring_trs]

        # checking regular season game...
        if game_type == 2:
            # ...for a shootout goal
            if 'SO' in score_periods_tds:
                shootout_game = True
                overtime_game = True
            # ...for an overtime goal
            elif 'OT' in score_periods_tds:
                overtime_game = True

        # checking playoff game...
        elif game_type == 3:
            # ...for an overtime goal, e.g. if there was a goal scored
            # in a period later than the third
            if max([int(x) for x in score_periods_tds]) > 3:
                overtime_game = True

        return overtime_game, shootout_game

    def retrieve_three_stars(self, game, teams, rosters, raw_data):
        """
        Retrieves the game's three star selections
        """
        three_stars_raw_data = raw_data.xpath(
            "//td[text() = 'OFFICIALS']/parent::tr/parent::table" +
            "/tr[2]/td[2]/table/tr/td/table/tr")

        i = 1
        # for every table row in raw data for three stars...
        for tr in three_stars_raw_data:
            # retrieving table cells from current row
            tds = tr.xpath("td/text()")
            # making sure we're looking at actual data (containing
            # exactly four table cells)
            if len(tds) == 4:
                # retrieving team abbreviation and player's number and name
                _, team_abbr, _, plr_number_name = tds
                # converting player's number
                no = int(plr_number_name.split()[0])
                # assuming star selection is from home team
                key = 'home'
                # otherwise adjusting key
                if team_abbr == teams['road'].orig_abbr:
                    key = 'road'
                # adding star selection's player id to game data
                if no in rosters[key]:
                    setattr(
                        game, "star_%d" % i, rosters[key][no].player_id)
            i += 1

        db_game = Game.find_by_id(game.game_id)
        create_or_update_db_item(db_game, game)

    def retrieve_referees(self, game_data):
        """
        Retrieves the game's referees.
        """
        referees = self.raw_data.xpath(
            "//td[text() = 'OFFICIALS']/parent::tr/parent::table" +
            "/tr/td/table/tr/td/table/tr/td[@align='left']/text()"
        )[:4]

        game_data['referee_1'] = referees[0]
        game_data['referee_2'] = referees[1]
        game_data['linesman_1'] = referees[2]
        game_data['linesman_2'] = referees[3]

        return game_data

    def link_game_with_teams(self, teams):
        """
        Adds team information to current game.
        """
        game_team_data = dict()

        # for both home and road team...
        for key in ['home', 'road']:
            curr_team = teams[key]
            # ...retrieving basic information for this team in current game
            game_team_data["%s_team" % key] = curr_team
            game_team_data["%s_team_id" % key] = curr_team.team_id
            game_team_data["%s_score" % key] = curr_team.score
            game_team_data["%s_overall_game_count" % key] = curr_team.game_no
            game_team_data["%s_game_count" % key] = curr_team.home_road_no
            game_team_data[curr_team.orig_abbr] = curr_team

        return game_team_data

    def create_team_games(self, game, gs_data):
        """
        Retrieves team related information for the current game.
        """
        # retrieving raw by period goals, shots, penalties and penalty minutes
        by_period = gs_data.xpath(
            "//td[@class='sectionheading']")[2].xpath(
                "parent::tr/following-sibling::tr")[0]
        by_period_goals, by_period_shots, by_period_pens, by_period_pims = \
            [by_period.xpath(
                ".//tr[@class='oddColor' or " +
                "@class='evenColor']/td[%d]/text()" % i) for i in range(2, 6)]

        # retrieving raw data for empty-net goals
        en_goals_raw_data = gs_data.xpath(
            "//td[@align='center' and contains(text(), '-EN')]")

        # retrieving raw powerplay opportunities and minutes
        pp_situations = gs_data.xpath(
            "//td[@class='sectionheading']")[3].xpath(
                "parent::tr/following-sibling::tr")[0]
        pp_5v4, pp_5v3, pp_4v3 = [pp_situations.xpath(
            ".//tr[@class='oddColor']/td[%d]/text()" % i) for i in range(1, 4)]

        team_games = dict()

        for key, key_against in zip(('road', 'home'), ('home', 'road')):

            # retrieving current team id based on current key
            team_id = getattr(game, "%s_team_id" % key)

            # setting team game data dictionary with basic information
            team_game_data = dict()
            team_game_data['home_road_type'] = key
            team_game_data['team_id'] = team_id
            team_game_data['score'] = getattr(game, "%s_score" % key)
            team_game_data['score_against'] = getattr(
                game, "%s_score" % key_against)

            # retrieving per period and overall shots and goals as well as
            # raw overall penalties and penalties in minutes from raw data
            team_game_data = self.retrieve_per_period_data(
                key, team_game_data,
                by_period_goals, by_period_shots,
                by_period_pens, by_period_pims)
            # retrieving power play opportunities and times from raw data
            team_game_data = self.retrieve_power_plays(
                key, team_game_data, [pp_5v4, pp_4v3, pp_5v3]
            )
            team_game_data = self.retrieve_win_loss_types(
                team_game_data, game.shootout_game, game.overtime_game)
            # retrieving empty net goals for and against
            team_game_data = self.retrieve_empty_net_goals(
                key, team_game_data, en_goals_raw_data)
            # retrieving shootout information (if applicable)
            if self.raw_so_data is not None:
                team_game_data = self.retrieve_shootout_attempts(
                    team_game_data
                )

            # trying to retrieve team game item with same team and game
            # ids from database
            team_game_db = TeamGame.find(game.game_id, team_id)
            # creating new team game item
            new_team_game = TeamGame(game.game_id, team_id, team_game_data)
            # creating new or updating existing team game item in database
            create_or_update_db_item(team_game_db, new_team_game)

            team_games[key] = TeamGame.find(game.game_id, team_id)

        return team_games

    def retrieve_win_loss_types(
            self, team_game_data, shootout_game, overtime_game):
        """
        Identifies win/loss situation for current team in current game.
        """
        # setting default values
        for item in [
            'win', 'loss', 'tie', 'shootout_win', 'shootout_loss',
            'overtime_win', 'overtime_loss', 'regulation_win',
            'regulation_loss'
        ]:
            team_game_data[item] = 0

        # if current team's score is higher than the other one's, we have a win
        if team_game_data['score'] > team_game_data['score_against']:
            team_game_data['win'] = 1
            # determining type of win
            if shootout_game:
                team_game_data['shootout_win'] = 1
            elif overtime_game:
                team_game_data['overtime_win'] = 1
            else:
                team_game_data['regulation_win'] = 1
        # if current team's score is lower than the other one's, we have a loss
        elif (
            team_game_data['score'] < team_game_data['score_against']
        ):
            team_game_data['loss'] = 1
            # determining type of loss
            if shootout_game:
                team_game_data['shootout_loss'] = 1
            elif overtime_game:
                team_game_data['overtime_loss'] = 1
            else:
                team_game_data['regulation_loss'] = 1
        # otherwise we have a tie
        else:
            team_game_data['tie'] = 1

        # calculating points based on win/loss types
        points = 0

        if 'win' in team_game_data:
            points += team_game_data['win'] * 2
        if 'overtime_loss' in team_game_data:
            points += team_game_data['overtime_loss']
        if 'shootout_loss' in team_game_data:
            points += team_game_data['shootout_loss']
        team_game_data['points'] = points

        return team_game_data

    def retrieve_empty_net_goals(self, key, team_game_data, en_goals_raw_data):
        """
        Retrieves empty-net goals for and against for current team in current
        game.
        """
        # setting default values
        team_game_data['empty_net_goals_for'] = 0
        team_game_data['empty_net_goals_against'] = 0

        # iterating over all table cells with empty net goal indication
        for td in en_goals_raw_data:
            # finding team that scored the empty net goal
            en_goal_team_abbr = td.xpath(
                "following-sibling::td[1]/text()").pop(0)
            en_goal_team = Team.find_by_abbr(en_goal_team_abbr)
            # setting empty net goal count accordingly
            if en_goal_team.team_id == team_game_data['team_id']:
                team_game_data['empty_net_goals_for'] += 1
            else:
                team_game_data['empty_net_goals_against'] += 1

        return team_game_data

    def retrieve_power_plays(self, key, team_game_data, pp_raw_data):
        """
        Analyzes power play raw data to yield database-ready information.
        """
        # initial power play opportunities and time
        team_game_data['pp_time_overall'] = str_to_timedelta("00:00")
        team_game_data['pp_overall'] = 0
        team_game_data['pp_goals_overall'] = 0

        # depending on which team is currently handled, a different component
        # of the raw data has to be used
        if key == 'road':
            pp_idx = 0
        else:
            pp_idx = -1

        # setting up lists of power play types and power play time types
        pp_types = ['pp_5v4', 'pp_5v3', 'pp_4v3']
        pp_time_types = ['pp_time_5v4', 'pp_time_5v3', 'pp_time_4v3']
        pp_goal_types = ['pp_goals_5v4', 'pp_goals_5v3', 'pp_goals_4v3']

        # populating power play types with goals scored, opportunity count and
        # minutes played
        for pp_raw in pp_raw_data:
            try:
                pp_goals, pp_opps = [
                    int(x) for x in pp_raw[pp_idx].split("/")[0].split("-")]
                pp_time = str_to_timedelta(pp_raw[pp_idx].split("/")[-1])
            except:
                pp_goals = 0
                pp_opps = 0
                pp_time = str_to_timedelta("00:00")
            finally:
                team_game_data['pp_overall'] += pp_opps
                team_game_data[pp_types.pop(0)] = pp_opps
                team_game_data['pp_time_overall'] += pp_time
                team_game_data[pp_time_types.pop(0)] = pp_time
                team_game_data['pp_goals_overall'] += pp_goals
                team_game_data[pp_goal_types.pop(0)] = pp_goals

        return team_game_data

    def retrieve_per_period_data(
            self, key, team_game_data,
            by_period_goals, by_period_shots, by_period_pens, by_period_pims):
        """
        Analyzes per-period raw data to yield per-team, per-period goals and
        shots. Additionally retrieves per-team penalty data.
        """
        (road_gf, home_gf) = (
            by_period_goals[:len(by_period_goals) // 2],
            by_period_goals[len(by_period_goals) // 2:]
        )
        (road_sf, home_sf) = (
            by_period_shots[:len(by_period_shots) // 2],
            by_period_shots[len(by_period_shots) // 2:]
        )
        (road_pens, home_pens) = (
            int(by_period_pens[:len(by_period_pens) // 2][-1]),
            int(by_period_pens[len(by_period_pens) // 2:][-1])
        )
        (road_pim, home_pim) = (
            int(by_period_pims[:len(by_period_pims) // 2][-1]),
            int(by_period_pims[len(by_period_pims) // 2:][-1])
        )

        # assuming current team is home team:
        team_gf, team_ga = home_gf, road_gf
        team_sf, team_sa = home_sf, road_sf
        team_pens, team_pim = home_pens, home_pim
        # otherwise switching/re-assigning values
        if key == 'road':
            team_gf, team_ga = team_ga, team_gf
            team_sf, team_sa = team_sa, team_sf
            team_pens, team_pim = road_pens, road_pim

        # adding penalty information to team game data dictionary
        team_game_data['penalties'] = team_pens
        team_game_data['pim'] = team_pim

        # setting goals for per period and overall
        self.set_goals_shots(team_game_data, "goals_for", team_gf)
        # setting shots for per period and overall
        self.set_goals_shots(team_game_data, "shots_for", team_sf)
        # setting goals against per period and overall
        self.set_goals_shots(team_game_data, "goals_against", team_ga)
        # setting shots against per period and overall
        self.set_goals_shots(team_game_data, "shots_against", team_sa)

        # aggregating overtime shots (if applicable)
        team_ot_sf = team_sf[3:-1]
        team_ot_sa = team_sa[3:-1]

        if team_ot_sf or team_ot_sa:
            shots_for_ot = 0
            shots_against_ot = 0

            for ot_sf, ot_sa in zip(team_ot_sf, team_ot_sa):
                shots_for_ot += int(ot_sf)
                shots_against_ot += int(ot_sa)

            team_game_data['shots_for_ot'] = shots_for_ot
            team_game_data['shots_against_ot'] = shots_against_ot

        return team_game_data

    def set_goals_shots(self, team_game_data, data_key, source):
        """
        Sets goals/shots for/against in for team an current game both overall
        and per period.
        """
        # setting overall count for goals/shots for/against
        team_game_data[data_key] = int(source[-1])
        # setting per period count for goals/shots for/against
        for k, v in zip(self.PER_PERIOD_ORDINALS, [int(x) for x in source]):
            team_game_data["_".join((data_key, k))] = v

        return team_game_data

    def retrieve_shootout_attempts(self, team_game_data):
        """
        Retrieves shootout attempts/goals for team involved in current game.
        """
        # setting index to get road team shootout information from raw data
        idx = 2
        # increasing index variable to get home team shootout information
        if team_game_data['home_road_type'] == 'home':
            idx += 1
        # setting up xpath expression to retrieve shootout information
        xpath_expr = "//td[contains(text(), 'Shootout Summary')]/ancestor::"\
            "tr/following-sibling::tr[1]/td/table/tr[%d]/td/text()" % idx
        # applying xpath expression
        so_data = self.raw_so_data.xpath(xpath_expr)

        # retrieving number of goals scored in shootout
        team_game_data['so_goals'] = int(so_data[1])
        # summing up shots, misses and penalties to retrieve number of attempts
        team_game_data['so_attempts'] = sum([int(x) for x in so_data[2:]])

        return team_game_data

    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        # finding content of html element with *GameInfo*-id
        game_data_str = self.raw_data.xpath(
            "//table[@id='GameInfo']/tr/td/text()")
        game_data_str = [re.sub("\s+", " ", s) for s in game_data_str]
        self.game_data = remove_null_strings(game_data_str)[-5:]
