#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging
from collections import defaultdict
from operator import add

from utils import str_to_timedelta, reverse_num_situation
from utils.event_matcher import is_matching_event
from db import create_or_update_db_item, commit_db_item
from db.team import Team
from db.event import Event
from db.shot import Shot
from db.goal import Goal
from db.penalty import Penalty
from db.miss import Miss
from db.block import Block
from db.faceoff import Faceoff
from db.hit import Hit
from db.giveaway import Giveaway
from db.takeaway import Takeaway
from db.shootout_attempt import ShootoutAttempt
from db.shot_attempt import ShotAttempt

logger = logging.getLogger(__name__)


class EventParser():

    # regular expressions for retrieving...
    # ... the zone where an event happened
    ZONE_REGEX = re.compile(",?\s((Off|Def|Neu)\.)\sZone")
    # ... number of a player shooting on goal
    PLAYER_REGEX = re.compile("(ONGOAL - |#)(\d{1,2})\s(\w+\'?\s?\w+),?")
    # ... shot type and distance from goal for a shot
    SHOT_REGEX = re.compile(",\s(.+),.+,\s(.+)\sft\.(Assist)?")
    # ... shot type and distance from goal for a shot when no zone is specified
    SHOT_WO_ZONE_REGEX = re.compile(",\s(.+),\s(.+)\sft\.(Assist)?")
    # ... the distance from goal for a shot
    DISTANCE_REGEX = re.compile("(\d+)\sft\.")
    # ... assistants to a goal
    ASSIST_REGEX = re.compile("Assists?:\s(.+)(?:;\s(.+))?")
    # ... the number of player scoring a goal or assist
    SCORER_NO_REGEX = re.compile("#(\d+)?")
    # ... a penalty infraction for a player
    INFRACTION_REGEX = re.compile(
        "#\d+.{1}[A-Z]+(\'| |\.|\-){0,2}(?:[A-Z ]+)?\.?.{1}([A-Z].+)\(\d")
    # ... a penalty infraction for a team
    TEAM_INFRACTION_REGEX = re.compile("(.{3})\sTEAM(.+)\(\d")
    # ... a penalty infraction for a team but without anyone serving it
    ANONYMOUS_TEAM_INFRACTION_REGEX = re.compile("Team(.+)\-.+bench")
    # ... a penalty infraction for a coach
    COACH_INFRACTION_REGEX = re.compile("#(.+coach)\(\d+")
    # ... the number penalty minutes assessed for an infraction
    PIM_REGEX = re.compile("\((\d+)\smin\)")
    # ... the number of player taking a penalty
    PENALTY_NO_REGEX = re.compile("^.{3}\s#(\d+)")
    # ... number and team of player drawing a penalty
    PENALTY_DRAWN_REGEX = re.compile("Drawn By:\s(.{3}).+#(\d+)")
    # ...  number of player serving a penalty
    SERVED_BY_REGEX = re.compile("Served By:\s#(\d+)\s(.+)")
    # ... teams and numbers of players involved in hit/blocked shot
    HIT_BLOCK_REGEX = re.compile(
        "(.{3})\s#(\d{1,2})\s.+(?:(?:HIT)|" +
        "(?:BLOCKED BY))\s+(.{3})\s#(\d{1,2})\s.+")
    # ... teams involved in hit, number of player taking the hit
    ONLY_HIT_TAKEN_REGEX = re.compile("HIT\s+(.{3})\s#(\d{1,2})\s.+")
    # ... teams involved in hit, number of player hitting
    ONLY_HIT_GIVEN_REGEX = re.compile(
        "(.{3})\s#(\d{1,2})\s.+HIT\s+(.{3})\s#.+")
    # ... number and team of player blocking a shot
    ONLY_BLOCKED_BY_REGEX = re.compile("BLOCKED BY\s+(.{3})\s#(\d{1,2})\s.+")
    # ... shot type of a blocked shot
    BLOCKED_SHOT_TYPE_REGEX = re.compile(",\s(.+),")
    # ... numbers of players participating in a faceoff
    FACEOFF_NO_REGEX = re.compile(".{3}\s#(\d{1,2}).+.{3}\s#(\d{1,2})")

    # official game information json data uses other type denominators than the
    # official play-by-play summaries (and subsequently the database)
    # this mapping associates json play types with the corresponding event
    # types in the play-by-play summaries
    PLAY_EVENT_TYPE_MAP = {
        "GIVEAWAY": "GIVE", "BLOCKED_SHOT": "BLOCK", "PENALTY": "PENL",
        "MISSED_SHOT": "MISS", "SHOT": "SHOT", "FACEOFF": "FAC",
        "TAKEAWAY": "TAKE", "HIT": "HIT"
    }
    # official game information json data uses pre-defined player types to
    # indicate the role a player has with regard to a certain play
    # this mapping associates play types with the according player types as
    # utilized in the json data
    PLAY_PLAYER_TYPES = {
        'FAC': ('Winner', 'Loser'), 'HIT': ('Hitter', 'Hittee'),
        'BLOCK': ('Blocker', 'Shooter'), 'GOAL': ('Scorer',),
        'SHOT': ('Shooter',), 'MISS': ('Shooter',),
        'PENL': ("PenaltyOn", "DrewBy"), 'GIVE': ("PlayerID",),
        'TAKE': ("PlayerID",)
    }
    SHOT_TYPES = [
        'Wrist', 'Snap', 'Backhand',
        'Wrap-around', 'Slap', 'Deflected', 'Tip-In']
    MISS_TYPES = ['Hit Crossbar', 'Wide of Net', 'Over Net', 'Goalpost']

    def __init__(self, raw_data, json_data, raw_gs_data):
        self.raw_data = raw_data
        self.json_data = json_data
        self.raw_gs_data = raw_gs_data
        # class-wide variables to hold current score for both home and road
        # team, increase accordingly if a goal was score
        self.score = defaultdict(int)
        # class-wide variable for score differential
        self.score_diff = 0

    def create_events(self, game, rosters):
        """
        Creates and specifies event items.
        """
        self.game = game
        self.rosters = rosters

        # pre-processing play-by-play summary
        self.load_data()
        # caching plays with coordinates from json game summary
        self.cache_plays_with_coordinates()
        # creating dictionary for all goals scored and the corresponding
        # numerical situation
        self.cache_goals()

        for event_data_item in self.event_data:
            # setting event item with basic information
            event = self.get_event(event_data_item)

            # specifying event further
            if self.game.type == 2 and event.period == 5:
                # shootout attempts are either goals, saved shots or misses all
                # occurring in the fifth period of a regular season game
                specific_event = self.get_shootout_attempt(event)
            else:
                # specifying regular play-by-play event
                specific_event = self.specify_event(event)

            if specific_event:
                print(specific_event)

            # determining coordinates in case current event is simultaneous
            # with others
            if specific_event is not None and None in [event.x, event.y]:
                event = self.find_coordinates_for_simultaneous_events(
                    specific_event)

            # skipping shot attempts conducted in a shootout
            if self.game.type == 2 and event.period == 5:
                pass
            # otherwise registering shot attempts
            else:
                if event.type in ['GOAL', 'SHOT', 'MISS', 'BLOCK']:
                    self.get_shot_attempt_event(event, specific_event)
                # re-calculating score differential after a goal
                if event.type == 'GOAL':
                    self.score_diff = self.score['home'] - self.score['road']

    def specify_event(self, event):
        """
        Specifies an event in more detail according to its type.
        """
        if event.type == 'SHOT':
            return self.get_shot_on_goal_event(event)

        if event.type == 'GOAL':
            shot = self.get_shot_on_goal_event(event)
            return self.get_goal_event(event, shot)

        if event.type == 'MISS':
            return self.get_missed_shot_event(event)

        if event.type == 'BLOCK':
            return self.get_block_event(event)

        if event.type == 'FAC':
            return self.get_faceoff_event(event)

        if event.type == 'HIT':
            return self.get_hit_event(event)

        if event.type == 'GIVE':
            return self.get_giveaway_event(event)

        if event.type == 'TAKE':
            return self.get_takeaway_event(event)

        if event.type == 'PENL':
            return self.get_penalty_event(event)

    def get_event(self, event_data_item):
        """
        Gets basic event information first and triggers type-specific parsing
        afterwards.
        """
        # retrieving data item contents as list
        tokens = event_data_item.xpath("td/text()")
        # setting up event data dictionary
        event_data_dict = dict()
        # TODO: decide whether to put game id directly in constructor
        event_data_dict['game_id'] = self.game.game_id
        event_data_dict['home_score'] = self.score['home']
        event_data_dict['road_score'] = self.score['road']

        # retrieving basic event attributes
        event_data_dict['in_game_event_cnt'] = int(tokens[0])
        event_data_dict['period'] = int(tokens[1])
        event_data_dict['num_situation'] = tokens[2].strip()
        event_data_dict['time'] = str_to_timedelta(tokens[3])
        event_data_dict['type'] = tokens[5]
        event_data_dict['raw_data'] = tokens[6]
        if tokens[7].strip():
            event_data_dict['raw_data'] = "|".join((
                event_data_dict['raw_data'], tokens[7]))

        # stoppages in play are registered as property of the according event
        if event_data_dict['type'] == 'STOP':
            event_data_dict['stop_type'] = event_data_dict['raw_data'].lower(
                ).replace("|", "")

        # retrieving players on goalies on ice for current event
        players_on_ice, goalies_on_ice = self.retrieve_players_on_ice(
            event_data_item)
        for key in ['home', 'road']:
            event_data_dict["%s_on_ice" % key] = players_on_ice[key]
            if key in goalies_on_ice:
                event_data_dict["%s_goalie" % key] = goalies_on_ice[key]

        # matching current event data with play (bringing along coordinates)
        # in case of exactly one event of the same type at the same time
        play_key = (
            event_data_dict['period'],
            event_data_dict['time'],
            event_data_dict['type'])
        if play_key in self.json_dict:
            if len(self.json_dict[play_key]) == 1:
                single_play_dict = self.json_dict[play_key][0]
                event_data_dict['x'] = int(single_play_dict['x'])
                event_data_dict['y'] = int(single_play_dict['y'])

        # creating event id as combination of game id and in-game event count
        event_id = "{0:d}{1:04d}".format(
            self.game.game_id, event_data_dict['in_game_event_cnt'])

        # setting up new event item
        event = Event(event_id, event_data_dict)
        # trying to find existing event item in database
        db_event = Event.find(
            self.game.game_id, event_data_dict['in_game_event_cnt'])
        # updating existing or creating new event item
        create_or_update_db_item(db_event, event)

        return Event.find(
            self.game.game_id, event_data_dict['in_game_event_cnt'])

    def get_shootout_attempt(self, event):
        """
        Retrieves or creates a shootout attempt event.
        """
        # checking attempt type, e.g.. 'MISS', 'SHOT' or 'GOAL'
        if event.type not in ['GOAL', 'SHOT', 'MISS']:
            return

        shootout_data_dict = dict()

        shootout_data_dict['attempt_type'] = event.type

        if shootout_data_dict['attempt_type'] == 'MISS':
            shootout_data_dict['on_goal'] = False
            shootout_data_dict['scored'] = False
        elif shootout_data_dict['attempt_type'] == 'SHOT':
            shootout_data_dict['on_goal'] = True
            shootout_data_dict['scored'] = False
        elif shootout_data_dict['attempt_type'] == 'GOAL':
            shootout_data_dict['on_goal'] = True
            shootout_data_dict['scored'] = True

        # retrieving team that attempted at shootout and zone where the shot
        # was taken
        team, zone = self.retrieve_standard_event_parameters(event)
        shootout_data_dict['team_id'] = team.team_id
        shootout_data_dict['zone'] = zone

        # retrieving shootout shooter and goalie
        no = int(self.PLAYER_REGEX.search(event.raw_data).group(2))

        # assuming shooter's team is home and goalie's team is road team
        plr_key, goalie_key = "home", "road"
        # otherwise swapping keys
        if team.team_id == self.game.road_team_id:
            plr_key, goalie_key = goalie_key, plr_key

        shootout_data_dict['player_id'] = self.rosters[plr_key][no].player_id
        shootout_data_dict['goalie_id'] = getattr(
            event, "%s_goalie" % goalie_key)
        shootout_data_dict['goalie_team_id'] = getattr(
            self.game, "%s_team_id" % goalie_key)

        # retrieving shot properties
        # TODO: re-factor (?)
        if ". Zone," in event.raw_data:
            try:
                so_attempt_props, distance = self.SHOT_REGEX.search(
                    event.raw_data).group(1, 2)
            except:
                so_attempt_props = None
                distance = self.DISTANCE_REGEX.search(event.raw_data).group(1)
                logger.warn(
                    "Couldn't retrieve shootout attempt properties " +
                    "from raw data: %s" % event.raw_data)
        else:
            so_attempt_props, distance = self.SHOT_WO_ZONE_REGEX.search(
                event.raw_data).group(1, 2)

        if so_attempt_props is not None:
            if shootout_data_dict['on_goal']:
                shootout_data_dict['shot_type'] = so_attempt_props
            else:
                shot_miss_types = [
                    token.strip() for token in so_attempt_props.split(',')]
                if len(shot_miss_types) == 2:
                    (
                        shootout_data_dict['shot_type'],
                        shootout_data_dict['miss_type']) = shot_miss_types
                else:
                    shootout_data_dict['shot_type'] = so_attempt_props
                    logger.warn(
                        "Couldn't retrieve shootout attempt miss " +
                        "type from raw data: %s" % event.raw_data)

        shootout_data_dict['distance'] = int(distance)

        # retrieving shootout attempt with same event id from database
        db_shootout_attempt = ShootoutAttempt.find_by_event_id(event.event_id)
        # creating new shootout attempt
        new_shootout_attempt = ShootoutAttempt(
            event.event_id, shootout_data_dict)
        # creating or updating shootout attempt item in database
        create_or_update_db_item(db_shootout_attempt, new_shootout_attempt)

        return ShootoutAttempt.find_by_event_id(event.event_id)

    def get_shot_attempt_event(self, event, specific_event):
        """
        Retrieves or creates a shot attempt event.
        """
        shot_attempt_dict = dict()

        shot_attempt_dict['shot_attempt_type'] = event.type[0]
        shot_attempt_dict['plus_minus'] = 1

        if not event.home_on_ice or not event.road_on_ice:
            logger.warn(
                "Unable to retrieve shot attempt as information about " +
                "players on ice is not available.")
            return

        # retrieving skaters for home and road teams, respectively
        shot_attempt_dict['home_skaters'] = list(set(
            event.home_on_ice).difference(set([event.home_goalie])))
        shot_attempt_dict['road_skaters'] = list(set(
            event.road_on_ice).difference(set([event.road_goalie])))

        # assuming the shooting team is the home team
        shot_attempt_for_key, shot_attempt_against_key = 'home', 'road'
        shot_attempt_dict['score_diff'] = self.score_diff
        # otherwise switching keys
        if specific_event.team_id == self.game.road_team_id:
            shot_attempt_for_key, shot_attempt_against_key = (
                shot_attempt_against_key, shot_attempt_for_key)
            shot_attempt_dict['score_diff'] = self.score_diff / -1

        if event.type in ('MISS', 'SHOT', 'GOAL'):
            # retrieving numerical situation and actual shooter
            shot_attempt_dict['num_situation'] = event.num_situation
            shot_attempt_dict['shooter_id'] = specific_event.player_id
            # goals are actually just shots that went by the goaltender
            if event.type == 'GOAL':
                shot_attempt_dict['shot_attempt_type'] = 'S'

        elif event.type == 'BLOCK':
            # retrieving reverse numerical situation and actual shooter
            shot_attempt_dict['num_situation'] = reverse_num_situation(
                event.num_situation)
            shot_attempt_dict['shooter_id'] = specific_event.blocked_player_id
            shot_attempt_for_key, shot_attempt_against_key = (
                shot_attempt_against_key, shot_attempt_for_key)
            shot_attempt_dict['score_diff'] = self.score_diff / -1

        shot_attempt_dict['shooting_team'] = getattr(
            self.game, "%s_team_id" % shot_attempt_for_key)
        shot_attempt_dict['other_team'] = getattr(
            self.game, "%s_team_id" % shot_attempt_against_key)
        shot_attempt_dict['plr_situation'] = "%dv%d" % (
            len(shot_attempt_dict["%s_skaters" % shot_attempt_for_key]),
            len(shot_attempt_dict["%s_skaters" % shot_attempt_against_key]))
        shot_attempt_dict['shot_attempt_for_player_ids'] = getattr(
            event, "%s_on_ice" % shot_attempt_for_key)
        shot_attempt_dict['shot_attempt_against_player_ids'] = getattr(
            event, "%s_on_ice" % shot_attempt_against_key)

        for player_id in shot_attempt_dict['shot_attempt_for_player_ids']:
            if shot_attempt_dict['shooter_id'] == player_id:
                shot_attempt_dict['actual'] = True
            else:
                shot_attempt_dict['actual'] = False

            new_shot_attempt = ShotAttempt(
                self.game.game_id, shot_attempt_dict['shooting_team'],
                event.event_id, player_id, shot_attempt_dict)

            db_shot_attempt = ShotAttempt.find_by_event_player_id(
                event.event_id, player_id
            )

            create_or_update_db_item(db_shot_attempt, new_shot_attempt)

        # reversing numerical situation, score differential and player
        # disposition between teams
        shot_attempt_dict['num_situation'] = reverse_num_situation(
            shot_attempt_dict['num_situation'])
        shot_attempt_dict['score_diff'] = shot_attempt_dict['score_diff'] / -1
        shot_attempt_dict['plr_situation'] = shot_attempt_dict[
            'plr_situation'][::-1]
        shot_attempt_dict['plus_minus'] = -1
        # re-setting player actually taking the shot attempt
        shot_attempt_dict['actual'] = False

        for player_id in shot_attempt_dict['shot_attempt_against_player_ids']:
            new_shot_attempt = ShotAttempt(
                self.game.game_id, shot_attempt_dict['other_team'],
                event.event_id, player_id, shot_attempt_dict)

            db_shot_attempt = ShotAttempt.find_by_event_player_id(
                event.event_id, player_id
            )

            create_or_update_db_item(db_shot_attempt, new_shot_attempt)

    def get_missed_shot_event(self, event):
        """
        Retrieves or creates a missed shot event.
        """
        miss_data_dict = dict()
        # retrieving the shooter's team and zone where the shot was taken
        team, zone = self.retrieve_standard_event_parameters(event)
        miss_data_dict['team_id'] = team.team_id
        miss_data_dict['zone'] = zone

        # retrieving the shooter's number
        no = int(self.PLAYER_REGEX.search(event.raw_data).group(2))

        # assuming shooter's team is home and goalie's team is road team
        plr_key, goalie_key = "home", "road"
        # otherwise swapping keys
        if team.team_id == self.game.road_team_id:
            plr_key, goalie_key = goalie_key, plr_key
        # retrieving shooter's player id
        miss_data_dict['player_id'] = self.rosters[plr_key][no].player_id
        # retrieving goalie's team and player id
        miss_data_dict['goalie_team_id'] = getattr(
            self.game, "%s_team_id" % goalie_key)
        miss_data_dict['goalie_id'] = getattr(event, "%s_goalie" % goalie_key)
        # checking whether current shot was a penalty shot
        if "penalty shot" in event.raw_data.lower():
            miss_data_dict['penalty_shot'] = True

        # retrieving combined missed shot properties from raw data
        miss_props, distance = self.SHOT_REGEX.search(
            event.raw_data).group(1, 2)
        # splitting up missed shot properties
        miss_props_tokens = [s.strip() for s in miss_props.split(',')]
        # sorting out missed shot properties to retrieve shot/miss type
        if len(miss_props_tokens) == 3 and miss_props_tokens[0].lower(
                ) == 'penalty shot':
                    shot_type, miss_type = miss_props_tokens[1:]
        elif len(miss_props_tokens) == 2:
            shot_type, miss_type = miss_props_tokens
        else:
            token = miss_props_tokens.pop()
            if token in self.SHOT_TYPES:
                shot_type = token
                miss_type = None
            elif token in self.MISS_TYPES:
                shot_type = None
                miss_type = token
            else:
                shot_type = None
                miss_type = None
                logger.warn(
                    "Couldn't retrieve unambigious shot or" +
                    "miss type from raw data: %s" % event.raw_data)
        # adding missed shot properties to data dictionary
        miss_data_dict['shot_type'] = shot_type
        miss_data_dict['miss_type'] = miss_type
        miss_data_dict['distance'] = int(distance)

        # retrieving missed shot with same event id from database
        db_miss = Miss.find_by_event_id(event.event_id)
        # creating new missed shot
        new_miss = Miss(event.event_id, miss_data_dict)
        # creating or updating shot item in database
        create_or_update_db_item(db_miss, new_miss)

        return Miss.find_by_event_id(event.event_id)

    def get_shot_on_goal_event(self, event):
        """
        Retrieves or creates a shot on goal event.
        """
        shot_data_dict = dict()
        # retrieving the shooter's team and zone where the shot was taken
        team, zone = self.retrieve_standard_event_parameters(event)
        # retrieving the shooter's number
        no = int(self.PLAYER_REGEX.search(event.raw_data).group(2))
        shot_data_dict['team_id'] = team.team_id
        shot_data_dict['zone'] = zone
        # assuming shooters' team is home and goalie's team is road team
        plr_key, goalie_key = "home", "road"
        # otherwise swapping keys
        if team.team_id == self.game.road_team_id:
            plr_key, goalie_key = goalie_key, plr_key
        # retrieving shooter's player id
        shot_data_dict['player_id'] = self.rosters[plr_key][no].player_id
        # retrieving goalie's team and player id
        shot_data_dict['goalie_team_id'] = getattr(
            self.game, "%s_team_id" % goalie_key)
        shot_data_dict['goalie_id'] = getattr(event, "%s_goalie" % goalie_key)
        # checking whether current shot was a penalty shot
        if "penalty shot" in event.raw_data.lower():
            shot_data_dict['penalty_shot'] = True
        # retrieving shot type and distance from goal
        try:
            if ". Zone," in event.raw_data:
                shot_type, distance = self.SHOT_REGEX.search(
                    event.raw_data).group(1, 2)
            else:
                shot_type, distance = self.SHOT_WO_ZONE_REGEX.search(
                    event.raw_data).group(1, 2)
            if "," in shot_type:
                shot_type = shot_type.split(",")[-1].strip()
            shot_data_dict['shot_type'] = shot_type
        except:
            distance = self.DISTANCE_REGEX.search(event.raw_data).group(1)
            logger.warn(
                "Unable to retrieve shot type from" +
                "raw data: %s" % event.raw_data)
        shot_data_dict['distance'] = int(distance)
        # adjusting scored flag
        if event.type == 'GOAL':
            shot_data_dict['scored'] = True

        # retrieving shot with same event id from database
        db_shot = Shot.find_by_event_id(event.event_id)
        # creating new shot on goal
        new_shot = Shot(event.event_id, shot_data_dict)
        # creating or updating shot item in database
        create_or_update_db_item(db_shot, new_shot)

        return Shot.find_by_event_id(event.event_id)

    def get_penalty_event(self, event):
        """
        Retrieves or creates a penalty event.
        """
        penalty_data_dict = dict()
        # retrieving the shooter's team and zone where the shot was taken
        team, zone = self.retrieve_standard_event_parameters(event)
        penalty_data_dict['team_id'] = team.team_id
        penalty_data_dict['zone'] = zone

        # retrieving number of player taking the penalty (if applicable)
        try:
            taken_by_no = int(re.search(
                self.PENALTY_NO_REGEX, event.raw_data).group(1))
        except:
            taken_by_no = None

        # retrieving number of player serving the penalty (if applicable)
        try:
            served_by_no, served_by_name = re.search(
                self.SERVED_BY_REGEX, event.raw_data).group(1, 2)
            served_by_no = int(served_by_no)
        except:
            served_by_no = None

        # retrieving team and number of player drawing the penalty (if
        # applicable)
        try:
            drawn_by_team, drawn_by_no = re.search(
                self.PENALTY_DRAWN_REGEX, event.raw_data).group(1, 2)
            drawn_by_no = int(drawn_by_no)
            drawn_by_team = Team.find_by_abbr(drawn_by_team)
        except:
            drawn_by_no = None
            drawn_by_team = None

        # for a start assuming home team is taking the penalty, road team
        # is drawing it
        team_key, team_drawn_key = 'home', 'road'
        # switching team roles if road team is actually taking the penalty
        if team.team_id == self.game.road_team_id:
            team_key, team_drawn_key = team_drawn_key, team_key

        # converting player number(s) to actual player id(s)
        if taken_by_no is not None:
            penalty_data_dict['player_id'] = self.rosters[team_key][
                taken_by_no].player_id
        if served_by_no is not None:
            penalty_data_dict['server_player_id'] = self.rosters[team_key][
                served_by_no].player_id
        if drawn_by_no is not None:
            penalty_data_dict['drawn_player_id'] = self.rosters[
                team_drawn_key][drawn_by_no].player_id
            penalty_data_dict['drawn_team_id'] = drawn_by_team.team_id

        # retrieving penalty-worthy infraction
        # searching for a regular/penalty shot infraction
        infraction_match = re.search(self.INFRACTION_REGEX, event.raw_data)
        if infraction_match:
            infraction = infraction_match.group(2).strip()
        else:
            logger.debug(
                "Couldn't retrieve regular infraction" +
                "from raw data: %s" % event.raw_data)
            infraction = None

        # searching for a possible team infraction
        if infraction is None:
            infraction_match = re.search(
                self.TEAM_INFRACTION_REGEX, event.raw_data)
            if infraction_match:
                infraction = infraction_match.group(2).strip()
            else:
                logger.debug(
                    "Couldn't retrieve team infraction" +
                    "from raw data: %s" % event.raw_data)
                infraction = None

        # searching for a possible anonymous team infraction
        if infraction is None:
            infraction_match = re.search(
                self.ANONYMOUS_TEAM_INFRACTION_REGEX, event.raw_data)
            if infraction_match:
                infraction = infraction_match.group(1).strip()
            else:
                logger.debug(
                    "Couldn't retrieve anonymous team infraction" +
                    "from raw data: %s" % event.raw_data)
                infraction = None

        # searching for a possible coach infraction
        if infraction is None:
            infraction_match = re.search(
                self.COACH_INFRACTION_REGEX, event.raw_data)
            if infraction_match:
                infraction = infraction_match.group(1).strip()
            else:
                logger.debug(
                    "Couldn't retrieve coach infraction" +
                    "from raw data: %s" % event.raw_data)
                infraction = None

        penalty_data_dict['infraction'] = infraction

        if infraction is None:
            logger.error(
                "Could not retrieve infraction from" +
                "raw data: %s (game_id: %s)" % (
                    event.raw_data, self.game.game_id))

        # retrieving the amount of penalty minutes assessed for this infraction
        penalty_data_dict['pim'] = int(
            re.search(self.PIM_REGEX, event.raw_data).group(1))

        # retrieving penalty with same event id from database
        db_penalty = Penalty.find_by_event_id(event.event_id)
        # creating new penalty
        new_penalty = Penalty(event.event_id, penalty_data_dict)
        # creating or updating penalty item in database
        create_or_update_db_item(db_penalty, new_penalty)

        return Penalty.find_by_event_id(event.event_id)

    def get_goal_event(self, event, shot):
        """
        Retrieves or creates a goal event.
        """
        self.check_adjust_goal_num_situation(event)
        goal_data_dict = dict()

        # transferring attributes from shot the goal was scored on
        goal_data_dict['team_id'] = shot.team_id
        goal_data_dict['goal_against_team_id'] = shot.goalie_team_id
        goal_data_dict['player_id'] = shot.player_id
        goal_data_dict['shot_id'] = shot.shot_id

        # determining whether this was an empty net goal, i.e. no opposing
        # goalie was on ice for the goal
        if shot.goalie_id is None:
            goal_data_dict['empty_net_goal'] = True

        # updating team scores and determining goal type
        # for a start assuming home team has scored the goal, road team
        # has allowed it
        team_gf_key, team_ga_key = 'home', 'road'
        # switching team roles if road team has actually scored the goal
        if shot.team_id == self.game.road_team_id:
            team_gf_key, team_ga_key = team_ga_key, team_gf_key
        # increasing team score
        self.score[team_gf_key] += 1
        if self.score[team_gf_key] == self.score[team_ga_key]:
            goal_data_dict['tying_goal'] = True
        if self.score[team_gf_key] == self.score[team_ga_key] + 1:
            goal_data_dict['go_ahead_goal'] = True

        # retrieving overall and team goal count in current game
        goal_data_dict['in_game_cnt'] = add(
            self.score[team_gf_key], self.score[team_ga_key])
        goal_data_dict['in_game_team_cnt'] = self.score[team_gf_key]

        # retrieving assistants
        if self.ASSIST_REGEX.search(event.raw_data):
            assists = self.ASSIST_REGEX.search(
                event.raw_data).group(1).split(';')
            assist_cnt = 0
            for a in assists:
                assist_cnt += 1
                # retrieving assistant's number
                no = int(self.SCORER_NO_REGEX.search(a).group(1))
                # retrieving player that was the assistant
                assistant = self.rosters[team_gf_key][no].player_id
                goal_data_dict["assist_%d" % assist_cnt] = assistant

        # retrieving goal with same event id from database
        db_goal = Goal.find_by_event_id(event.event_id)
        # creating new goal
        new_goal = Goal(event.event_id, goal_data_dict)
        # creating or updating penalty item in database
        create_or_update_db_item(db_goal, new_goal)

        return Goal.find_by_event_id(event.event_id)

    def get_block_event(self, event):
        """
        Retrieves or creates a block event.
        """
        block_data_dict = dict()
        # retrieving the shooter's team and zone where the shot was taken
        blocked_team, zone = self.retrieve_standard_event_parameters(event)
        block_data_dict['blocked_team_id'] = blocked_team.team_id
        block_data_dict['zone'] = zone

        # trying to retrieve blocking team and numbers of players involved
        try:
            blocked_player_no, team, player_no = re.search(
                self.HIT_BLOCK_REGEX, event.raw_data).group(2, 3, 4)
            blocked_player_no = int(blocked_player_no)
        except:
            logger.warn(
                "Couldn't retrieve blocked player" +
                "from raw data: %s" % event.raw_data)
            team, player_no = re.search(
                self.ONLY_BLOCKED_BY_REGEX, event.raw_data).group(1, 2)
            blocked_player_no = None
        player_no = int(player_no)

        # retrieving blocking team
        team = Team.find(team)
        block_data_dict['team_id'] = team.team_id
        # assuming blocker is from home and blocked player is from road team
        block_key, blocked_key = "home", "road"
        # otherwise swapping keys
        if team.team_id == self.game.road_team_id:
            block_key, blocked_key = blocked_key, block_key
        # retrieving blocker's player id
        block_data_dict['player_id'] = self.rosters[
            block_key][player_no].player_id
        # retrieving blocked player's player id
        if blocked_player_no:
            block_data_dict['blocked_player_id'] = self.rosters[
                blocked_key][blocked_player_no].player_id

        # retrieving type of the blocked shot
        try:
            shot_type = re.search(
                self.BLOCKED_SHOT_TYPE_REGEX, event.raw_data).group(1)
            block_data_dict['shot_type'] = shot_type
        except AttributeError:
            logger.warn(
                "Couldn't retrieve blocked shot type" +
                "from raw data: %s" % event.raw_data)

        # retrieving blocked shot with same event id from database
        db_block = Block.find_by_event_id(event.event_id)
        # creating new blocked shot
        new_block = Block(event.event_id, block_data_dict)
        # creating or updating blocked shot item in database
        create_or_update_db_item(db_block, new_block)

        return Block.find_by_event_id(event.event_id)

    def get_faceoff_event(self, event):
        """
        Retrieves or creates a faceoff event.
        """
        faceoff_data_dict = dict()
        # retrieving team winning the faceoff, numerical situation for
        # winning team and zone where the faceoff was conducted
        team, zone = self.retrieve_standard_event_parameters(event)
        faceoff_data_dict['team_id'] = team.team_id
        faceoff_data_dict['zone'] = zone

        # retrieving numbers of players participating in the faceoff
        road_plr_no, home_plr_no = [
            int(n) for n in re.search(
                self.FACEOFF_NO_REGEX, event.raw_data).group(1, 2)]
        # assuming faceoff winner is from home and loser is from road team
        won_key, lost_key = "home", "road"
        won_no, lost_no = home_plr_no, road_plr_no
        # otherwise swapping keys
        if team.team_id == self.game.road_team_id:
            won_key, lost_key = lost_key, won_key
            won_no, lost_no = lost_no, won_no
        # setting players and losing team accordingly
        faceoff_data_dict['player_id'] = self.rosters[
            won_key][won_no].player_id
        faceoff_data_dict['faceoff_lost_player_id'] = self.rosters[
            lost_key][lost_no].player_id
        faceoff_data_dict['faceoff_lost_team_id'] = getattr(
            self.game, "%s_team_id" % lost_key)

        # retrieving zone where the faceoff was lost
        # TODO: find a less awkward solution to do that
        if faceoff_data_dict['zone'] == "Neu":
            faceoff_data_dict['faceoff_lost_zone'] = faceoff_data_dict['zone']
        elif faceoff_data_dict['zone'] == "Off":
            faceoff_data_dict['faceoff_lost_zone'] = "Def"
        elif faceoff_data_dict['zone'] == "Def":
            faceoff_data_dict['faceoff_lost_zone'] = "Off"

        # retrieving faceoff with same event id from database
        db_faceoff = Faceoff.find_by_event_id(event.event_id)
        # creating new faceoff
        new_faceoff = Faceoff(event.event_id, faceoff_data_dict)
        # creating or updating faceoff item in database
        create_or_update_db_item(db_faceoff, new_faceoff)

        return Faceoff.find_by_event_id(event.event_id)

    def get_hit_event(self, event):
        """
        Retrieves or creates a hit event.
        """
        hit_data_dict = dict()
        # retrieving team committing the hit and zone where the hit occurred
        team, zone = self.retrieve_standard_event_parameters(event)
        hit_data_dict['team_id'] = team.team_id
        hit_data_dict['zone'] = zone

        # TODO: less awkward
        # trying to retrieve involved players' numbers and team taking the hit
        if self.HIT_BLOCK_REGEX.search(event.raw_data):
            plr_no, team_taken, plr_no_taken = self.HIT_BLOCK_REGEX.search(
                event.raw_data).group(2, 3, 4)
            plr_no = int(plr_no)
            plr_no_taken = int(plr_no_taken)
        # sometimes only one of the involved players is retrievable
        else:
            logger.warn(
                "Couldn't retrieve all involved players" +
                "in hit from raw data: %s" % event.raw_data)
            if self.ONLY_HIT_TAKEN_REGEX.search(event.raw_data):
                team_taken, plr_no_taken = self.ONLY_HIT_TAKEN_REGEX.search(
                    event.raw_data).group(1, 2)
                plr_no = None
                plr_no_taken = int(plr_no_taken)
            if self.ONLY_HIT_GIVEN_REGEX.search(event.raw_data):
                plr_no, team_taken = self.ONLY_HIT_GIVEN_REGEX.search(
                    event.raw_data).group(2, 3)
                plr_no_taken = None
                plr_no = int(plr_no)

        # setting team taking the hit
        team_taken = Team.find_by_abbr(team_taken)
        hit_data_dict['hit_taken_team_id'] = team_taken.team_id

        # assuming hitter is from home and hittee is from road team
        hit_key, taken_key = "home", "road"
        # otherwise swapping keys
        if team.team_id == self.game.road_team_id:
            hit_key, taken_key = taken_key, hit_key

        # setting players accordingly
        if plr_no:
            hit_data_dict['player_id'] = self.rosters[hit_key][
                plr_no].player_id
        if plr_no_taken:
            hit_data_dict['hit_taken_player_id'] = self.rosters[taken_key][
                plr_no_taken].player_id

        # retrieving hit with same event id from database
        db_hit = Hit.find_by_event_id(event.event_id)
        # creating new hit
        new_hit = Hit(event.event_id, hit_data_dict)
        # creating or updating hit item in database
        create_or_update_db_item(db_hit, new_hit)

        return Hit.find_by_event_id(event.event_id)

    def get_giveaway_event(self, event):
        """
        Retrieves or creates a giveaway event.
        """
        giveaway_data_dict = dict()
        # retrieving team committing the giveaway and zone where the puck
        # was given away
        team, zone = self.retrieve_standard_event_parameters(event)
        giveaway_data_dict['team_id'] = team.team_id
        giveaway_data_dict['zone'] = zone

        # retrieving the player who committed the giveaway
        no = int(self.PLAYER_REGEX.search(event.raw_data).group(2))
        # assuming giveaway was committed from home team
        giveaway_key, given_to_key = "home", "road"
        # otherwise swapping keys
        if team.team_id == self.game.road_team_id:
            giveaway_key, given_to_key = given_to_key, giveaway_key

        giveaway_data_dict['player_id'] = self.rosters[
            giveaway_key][no].player_id
        giveaway_data_dict['given_to_team_id'] = Team.find_by_id(
            getattr(self.game, "%s_team_id" % given_to_key)).team_id

        # retrieving giveaway with same event id from database
        db_giveaway = Giveaway.find_by_event_id(event.event_id)
        # creating new giveaway
        new_giveaway = Giveaway(event.event_id, giveaway_data_dict)
        # creating or updating giveaway item in database
        create_or_update_db_item(db_giveaway, new_giveaway)

        return Giveaway.find_by_event_id(event.event_id)

    def get_takeaway_event(self, event):
        """
        Retrieves or creates a takeaway event.
        """
        takeaway_data_dict = dict()
        # retrieving team executing the takeaway and zone where the puck
        # was taken away
        team, zone = self.retrieve_standard_event_parameters(event)
        takeaway_data_dict['team_id'] = team.team_id
        takeaway_data_dict['zone'] = zone

        # retrieving the player who executed the takeaway
        no = int(self.PLAYER_REGEX.search(event.raw_data).group(2))
        # assuming takeaway was executed from home team
        takeaway_key, taken_from_key = "home", "road"
        # otherwise swapping keys
        if team.team_id == self.game.road_team_id:
            takeaway_key, taken_from_key = taken_from_key, takeaway_key

        takeaway_data_dict['player_id'] = self.rosters[
            takeaway_key][no].player_id
        takeaway_data_dict['taken_from_team_id'] = Team.find_by_id(
            getattr(self.game, "%s_team_id" % taken_from_key)).team_id

        # retrieving takeaway with same event id from database
        db_takeaway = Takeaway.find_by_event_id(event.event_id)
        # creating new takeaway
        new_takeaway = Takeaway(event.event_id, takeaway_data_dict)
        # creating or updating takeaway item in database
        create_or_update_db_item(db_takeaway, new_takeaway)

        return Takeaway.find_by_event_id(event.event_id)

    def find_coordinates_for_simultaneous_events(self, specific_event):
        """
        Determines coordinates for simultaneous events of the same type.
        """
        # retrieving base event for specified specific event
        event = Event.find_by_id(specific_event.event_id)
        # retrieving plays of same type occurring at the same time from
        # registry of all plays
        plays = self.json_dict[(event.period, event.time, event.type)]
        # determining matching play (and coordinates) for current play
        for play in plays:
            if is_matching_event(play, specific_event):
                event.x = play['x']
                event.y = play['y']
                commit_db_item(event)
                break
        return event

    # TODO: include data dict to assign elements to
    def retrieve_standard_event_parameters(self, event):
        """
        Retrieves standard event parameters including concerned team, zone and
        numerical situation.
        """
        team = Team.find_by_abbr(event.raw_data[0:3])
        try:
            zone = re.search(self.ZONE_REGEX, event.raw_data).group(1)[0:3]
        except:
            logger.warn(
                "Couldn't retrieve zone from raw data: %s" % event.raw_data)
            if event.type in ['MISS', 'SHOT', 'GOAL']:
                zone = 'Off'
            else:
                zone = None
            logger.info("Set zone deliberately to %s" % zone)

        return team, zone

    def retrieve_players_on_ice(self, event_data_item):
        """
        Gets all players and goalies on ice for current event and each team.
        """
        # setting up data containers
        poi_data = dict()
        players_on_ice = defaultdict(list)
        goalies_on_ice = dict()

        try:
            # retrieving players on ice for current event
            poi_data['road'], poi_data['home'] = event_data_item.xpath(
                "td/table")
        except:
            return players_on_ice, goalies_on_ice

        for key in ['road', 'home']:
            # retrieving jersey numbers of players on ice for current event
            nos_on_ice = [int(n) for n in poi_data[key].xpath(
                "tr/td/table/tr/td/font/text()")]
            # retrieving positions of players on ice for current event
            pos_on_ice = [s for s in poi_data[key].xpath(
                "tr/td/table/tr/td/text()") if s.strip()]
            # checking whether as many numbers as positions have been retrieved
            if len(pos_on_ice) != len(nos_on_ice):
                logger.warn(
                    "Number of retrieved jersey numbers does not match " +
                    "number of retrieved positions: game id %d" % (
                        self.game.game_id))
                continue
            for no, pos in zip(nos_on_ice, pos_on_ice):
                # retrieving actual player from rosters of current game
                player = self.rosters[key][no]
                # and appending to list of players on ice
                players_on_ice[key].append(player.player_id)
                if pos == 'G':
                    goalies_on_ice[key] = player.player_id

        return players_on_ice, goalies_on_ice

    def cache_goals(self):
        """
        Caches goals, or better numerical situations in which goals are scored
        for later comparison with event numerical situations retrieved from
        play-by-play data.
        """
        self.cached_goals = dict()

        periods = self.raw_gs_data.xpath(
            "//td[contains(text(), 'Goal Scorer')]/parent::tr/" +
            "following-sibling::tr/td[2]/text()")
        times = self.raw_gs_data.xpath(
            "//td[contains(text(), 'Goal Scorer')]/parent::tr/" +
            "following-sibling::tr/td[3]/text()")
        num_situations = self.raw_gs_data.xpath(
            "//td[contains(text(), 'Goal Scorer')]/parent::tr/" +
            "following-sibling::tr/td[4]/text()")

        for period, time, num_situation in zip(periods, times, num_situations):
            # converting regular season overtime to *fourth* period
            if period == 'OT':
                period = '4'
            (
                # using a tuple of period and time interval as key
                self.cached_goals[(int(period), str_to_timedelta(time))]
            ) = (
                # using numerical situation of actual goal as value
                num_situation.split("-")[0]
            )

    def cache_plays_with_coordinates(self):
        """
        Caches plays from json game summary to be later used for linking with
        retrieved events.
        """
        self.json_dict = defaultdict(list)

        # events are called plays in json game summaries
        for play in self.json_data['liveData']['plays']['allPlays']:
            coords = play['coordinates']
            # we're only interested in plays that have coordinates
            if not coords:
                continue
            # retrieving period and time of the play
            play_period = play['about']['period']
            play_time = str_to_timedelta(play['about']['periodTime'])
            play_type = play['result']['eventTypeId']
            # converting json play type to play-by-play summary event type
            if play_type in self.PLAY_EVENT_TYPE_MAP:
                play_type = self.PLAY_EVENT_TYPE_MAP[play_type]
            # setting up dictionary for single play
            single_play_dict = dict()
            # adding play type to single play dictionary
            single_play_dict['play_type'] = play_type
            # adding coordinates and description to single play dictionary
            single_play_dict['period_type'] = play['about']['periodType']
            single_play_dict['x'] = coords['x']
            single_play_dict['y'] = coords['y']
            single_play_dict['description'] = play['result']['description']
            # adding players participating in play
            for player in play['players']:
                # 'active', e.g. blocking, hitting, faceoff-winning player
                if player['playerType'] == self.PLAY_PLAYER_TYPES[play_type][
                        0]:
                            single_play_dict['active'] = player['player']['id']
                            single_play_dict['active_name'] = player[
                                'player']['fullName']
                # 'passive', e.g. blocked, hit, faceoff-losing player
                else:
                    single_play_dict['passive'] = player['player']['id']
                    single_play_dict['passive_name'] = player[
                        'player']['fullName']
            # adding penalty minutes to single play dictionary (if applicable)
            if play_type == 'PENL':
                single_play_dict['pim'] = play[
                    'result']['penaltyMinutes']
                infraction = play['result']['secondaryType'].lower()
                severity = play['result']['penaltySeverity'].lower()
                single_play_dict[
                    'infraction'] = self.adjust_penalty_infraction(
                        infraction, severity)
            if play_type in ['SHOT', 'GOAL']:
                single_play_dict['shot_type'] = play['result'][
                    'secondaryType'].lower().replace("shot", "").strip()
            # adding single player dictionary to dictionary of all plays using
            # period, time and type of play as key
            self.json_dict[(play_period, play_time, play_type)].append(
                single_play_dict
            )
        # TODO: logging multiple events of same type at the same time
        # for ptp, pti, pty in sorted(self.json_dict.keys()):
        #     if len(self.json_dict[(ptp, pti, pty)]) > 1:
        #         print(self.game.game_id, ptp, pti, pty)
        #         for entry in self.json_dict[(ptp, pti, pty)]:
        #             for key in entry:
        #                 print("\t", key, ":", entry[key])
        #             print("-----")

    def check_adjust_goal_num_situation(self, event):
        """
        Checks (and optionally adjusts) numerical situation of the specified
        event by comparing with previously cached goal data. If the goal was
        officially registered at a different numerical situation, the
        according event is updated.
        """
        if (event.period, event.time) in self.cached_goals:
            goal_num_situation = self.cached_goals[(event.period, event.time)]
            if event.num_situation != goal_num_situation:
                event.num_situation = goal_num_situation
                commit_db_item(event)

    def adjust_penalty_infraction(self, infraction, severity):
        """
        Adjusts the penalty infraction retrieved from json data to match
        corresponding information in database.
        """
        if infraction == 'too many men on the ice':
            infraction = "too many men/ice"
        if severity == 'major' and not infraction.strip().endswith('(maj)'):
            infraction = " ".join((infraction.strip(), '(maj)'))
        if severity == 'bench minor' and not infraction.strip().endswith(
                'bench'):
                    infraction = " - ".join((infraction.strip(), 'bench'))
        if severity == 'misconduct' and not infraction.strip().endswith(
                '(10 min)'):
                    infraction = " ".join((infraction.strip(), '(10 min)'))
        return infraction

    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        self.event_data = list()
        # finding all table rows on play-by-play page
        for tr in self.raw_data.xpath("body/table/tr"):
            # adding table row to play-by-play info if the first entry is a
            # digit, i.e. an in-game event id
            try:
                int(tr.xpath("td[1]/text()")[0])
                self.event_data.append(tr)
                # checking whether exactly eight table cells are located in row
                if len(tr.xpath("td")) != 8:
                    logger.warn(
                        "Unexpected number of table cells in play-by-play" +
                        "table row: %d" % len(tr.xpath("td")))
            except:
                logger.debug(
                    "Skipping row in play-by-play table")
                continue
