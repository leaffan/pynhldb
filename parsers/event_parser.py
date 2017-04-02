#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging
from collections import defaultdict

from utils import str_to_timedelta
from db import create_or_update_db_item
from db.team import Team
from db.event import Event
from db.shot import Shot
from db.penalty import Penalty

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
    # ... the number of a player serving a penalty
    SERVED_BY_REGEX = re.compile("Served By:\s#(\d+)\s(.+)")

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

    def __init__(self, raw_data, json_data):
        self.raw_data = raw_data
        self.json_data = json_data
        # class-wide variables to hold current score for both home and road
        # team, increase accordingly if a goal was score
        self.home_score = 0
        self.road_score = 0
        self.score_diff = 0
        # self.curr_period = 0

    def create_events(self, game, rosters):
        self.game = game
        self.rosters = rosters

        self.load_data()

        return

        for event_data_item in self.event_data:
            event = self.get_event(event_data_item)

            if self.game.type == 2 and event.period == 5:
                # shootout attempts are either goals, saved shots or misses all
                # occurring in the fifth period of a regular season game
                # shootout_attempt = self.get_shootout_attempt(event)
                pass
            else:
                # specifying regular play-by-play event
                self.specify_event(event)

    def retrieve_standard_event_parameters(self, event):
        """
        Retrieves standard event parameters including concerned team, zone and
        numerical situation.
        """
        team = Team.find_by_abbr(event.raw_data[0:3])
        try:
            zone = re.search(self.ZONE_REGEX, event.raw_data).group(1)
        except:
            logger.warn(
                "Couldn't retrieve zone from raw data: %s" % event.raw_data)
            if event.type in ['MISS', 'SHOT', 'GOAL']:
                zone = 'Off.'
            else:
                zone = None
            logger.info("Set zone deliberately to %s" % zone)

        return team, zone

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
        shot_data_dict['zone'] = zone[0:3]
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
        penalty_data_dict['zone'] = zone[0:3]
        # retrieving number of player serving the penalty (if applicable)
        try:
            served_by_no, served_by_name = re.search(
                self.SERVED_BY_REGEX, event.raw_data).group(1, 2)
            penalty_data_dict['served_by_no'] = int(served_by_no)
        except:
            penalty_data_dict['served_by_no'] = None

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
            return

        penalty = Penalty(event.event_id, penalty_data_dict)

        return penalty

    def specify_event(self, event):
        """
        Specifies an event in more detail according to its type.
        """
        if event.type in ['SHOT', 'GOAL']:
            shot = self.get_shot_on_goal_event(event)
            print(shot.shot_id)

        # if event.type == 'GOAL':
        #     shot = Shot.find_by_event_id(event.event_id)
        #     goal = self.get_goal_event(event, shot)

        # if event.type == 'MISS':
        #     miss = self.get_miss_event(event)

        # if event.type == 'BLOCK':
        #     block = self.get_block_event(event)

        # if event.type == 'FAC':
        #     faceoff = self.get_faceoff_event(event)

        # if event.type == 'HIT':
        #     hit = self.get_hit_event(event)

        # if event.type == 'GIVE':
        #     giveaway = self.get_giveaway_event(event)

        # if event.type == 'TAKE':
        #     takeaway = self.get_takeaway_event(event)

        if event.type == 'PENL':
            penalty = self.get_penalty_event(event)
            print(penalty.penalty_id)

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
        event_data_dict['home_score'] = self.home_score
        event_data_dict['road_score'] = self.road_score

        # retrieving basic event attributes
        event_data_dict['in_game_event_cnt'] = int(tokens[0])
        event_data_dict['period'] = int(tokens[1])
        event_data_dict['num_situation'] = tokens[2].strip()
        event_data_dict['time'] = str_to_timedelta(tokens[3])
        event_data_dict['type'] = tokens[5]
        event_data_dict['raw_data'] = tokens[6]

        # stoppages in play are registered as property of the according event
        if event_data_dict['type'] == 'STOP':
            event_data_dict['stop_type'] = event_data_dict['raw_data'].lower()

        # retrieving players on goalies on ice for current event
        players_on_ice, goalies_on_ice = self.retrieve_players_on_ice(
            event_data_item)
        for key in ['home', 'road']:
            event_data_dict["%s_on_ice" % key] = players_on_ice[key]
            if key in goalies_on_ice:
                event_data_dict["%s_goalie" % key] = goalies_on_ice[key]

        # play_key = (
        #     event_data_dict['period'],
        #     event_data_dict['time'],
        #     event_data_dict['type'])
        # if play_key in self.json_dict:
        #     if len(self.json_dict[play_key]) == 1:
        #         event_data_dict['x'] = int(
        #             self.json_dict[play_key][0][0]['x'])
        #         event_data_dict['y'] = int(
        #             self.json_dict[play_key][0][0]['y'])

        # creating event id
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

    def retrieve_players_on_ice(self, event_data_item):
        """
        Gets all players and goalies on ice for current event and each team.
        """
        poi_data = dict()
        players_on_ice = defaultdict(list)
        goalies_on_ice = dict()

        try:
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
                "tr/td/table/tr/td/text()") if s not in ['\r\n', '\n']]
            # checking whether as many numbers as positions have been retrieved
            if len(pos_on_ice) != len(nos_on_ice):
                logger.warn(
                    "Number of retrieved jersey numbers does not match" +
                    "number of retrieved positions: game id %d, period %d" % (
                        self.game.game_id, self.curr_period))
                continue
            for no, pos in zip(nos_on_ice, pos_on_ice):
                # retrieving actual player from rosters of current game
                player = self.rosters[key][no]
                # and appending to list of players on ice
                players_on_ice[key].append(player.player_id)
                if pos == 'G':
                    goalies_on_ice[key] = player.player_id

        return players_on_ice, goalies_on_ice

    def load_data(self):
        """
        Loads structured raw data and pre-processes it.
        """
        from collections import defaultdict
        self.json_dict = defaultdict(list)

        # TODO: cache plays and coordinates from json for later lookup
        for play in self.json_data['liveData']['plays']['allPlays']:
            coords = play['coordinates']
            if not coords:
                continue
            play_type = play['result']['eventTypeId']
            if play_type in self.PLAY_EVENT_TYPE_MAP:
                play_type = self.PLAY_EVENT_TYPE_MAP[play_type]
            play_time = str_to_timedelta(play['about']['periodTime'])
            play_period = play['about']['period']
            single_play_dict = dict()
            single_play_dict['x'] = coords['x']
            single_play_dict['y'] = coords['y']
            single_play_dict['description'] = play['result']['description']

            for player in play['players']:
                if player['playerType'] == self.PLAY_PLAYER_TYPES[play_type][0]:
                    single_play_dict['active'] = player['player']['id']
                    single_play_dict['active_name'] = player[
                        'player']['fullName']
                else:
                    single_play_dict['passive'] = player['player']['id']
                    single_play_dict['passive_name'] = player[
                        'player']['fullName']

            if play_type == 'PENL':
                single_play_dict['penalty_minutes'] = play[
                    'result']['penaltyMinutes']
            self.json_dict[(play_period, play_time, play_type)].append(
                single_play_dict
            )

        for ptp, pti, pty in sorted(self.json_dict.keys()):
            if len(self.json_dict[(ptp, pti, pty)]) > 1:
                print(self.game.game_id, ptp, pti, pty)
                for entry in self.json_dict[(ptp, pti, pty)]:
                    for key in entry:
                        print("\t", key, ":", entry[key])
                    print("-----")

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
