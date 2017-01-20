#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

import requests

from db.common import session_scope
from db.team import Team
from db.player_season import PlayerSeason


class PlayerDataRetriever():

    NHL_SITE_PREFIX = "http://statsapi.web.nhl.com/api/v1/people/"

    # input player data json keys
    JSON_KEY_FIRST_NAME = "firstName"
    JSON_KEY_LAST_NAME = "lastName"
    JSON_KEY_FULL_NAME = "fullName"
    JSON_KEY_POSITION = "primaryPosition"
    JSON_KEY_POSITION_CODE = "code"
    JSON_KEY_NUMBER = "primaryNumber"
    JSON_KEY_HEIGHT = "height"
    JSON_KEY_WEIGHT = "weight"
    JSON_KEY_HAND = "shootsCatches"
    JSON_KEY_DATE_OF_BIRTH = "birthDate"
    JSON_KEY_PLACE_OF_BIRTH_CITY = "birthCity"
    JSON_KEY_PLACE_OF_BIRTH_STATE_PROVINCE = "birthStateProvince"
    JSON_KEY_PLACE_OF_BIRTH_COUNTRY = "birthCountry"

    # database player data keys
    DB_KEY_FIRST_NAME = "first_name"
    DB_KEY_LAST_NAME = "last_name"
    DB_KEY_FULL_NAME = "full_name"
    DB_KEY_POSITION = "position"
    DB_KEY_NUMBER = "number"
    DB_KEY_HEIGHT = "height"
    DB_KEY_WEIGHT = "weight"
    DB_KEY_HAND = "hand"
    DB_KEY_DATE_OF_BIRTH = "date_of_birth"
    DB_KEY_PLACE_OF_BIRTH = "place_of_birth"

    def __init__():
        self.lock = threading.lock()

    def retrieve_raw_season_data(self, player_id):

        url = "".join((self.NHL_SITE_PREFIX, str(player_id)))
        r = requests.get(url, params={
            'expand': 'person.stats',
            'stats': 'yearByYear,yearByYearPlayoffs'})
        plr_json = r.json()

        plr_season_dict = dict()

        for person in plr_json['people']:
            plr_season_dict['position'] = person['primaryPosition']['code']
            for stats_type in person['stats']:
                for split in stats_type['splits']:

                    # skipping any stat line that does not refer to the NHL
                    if split['league']['name'] != "National Hockey League":
                        continue

                    # retrieving season type for current stat line, i.e.
                    # regular season or playoffs
                    if stats_type['type']['displayName'] == "yearByYear":
                        season_type = 'RS'
                    elif stats_type['type']['displayName'] == "yearByYearPlayoffs":
                        season_type = 'PO'

                    # retrieving season and team of current statline
                    season = int(split['season'][:4])
                    team = Team.find_by_id(split['team']['id'])
                    # retrieving sequence number of current statline,
                    # important in case of a player playing for multiple teams
                    # in one season
                    team_season_cnt = split['sequenceNumber']

                    # adding current stat line to dictionary container
                    plr_season_dict[
                        (season, season_type, team_season_cnt, team)
                    ] = split['stat']

        return plr_season_dict

    def create_or_update_player_season(self, plr_season, plr_season_db):
        with session_scope() as session:
            if not plr_season_db or plr_season_db is None:
                # logger.debug("Adding %s season to database: %s"
                #  % (NHLPlayer.find_by_id(plr_season.player_id), plr_season))
                session.add(plr_season)
                session.commit()
                if self.lock:
                    self.lock.acquire()
                # print("+ Added season statistics for %s" % player)
                # print("\t%s" % plr_season)
                if self.lock:
                    self.lock.release()
            else:
                if plr_season_db != plr_season:
                    plr_season_db.update(plr_season)
                    # logger.debug("Updating %s season
                    #  in database: %s" % (NHLPlayer.find_by_id(
                    # plr_season_db.player_id), plr_season_db))
                    session.merge(plr_season_db)
                    session.commit()
                    # locked_print(["+ Updated season
                    # statistics for %s" % player,
                    #  "\t%s" % plr_season_db], lock)

    def retrieve_player_seasons(self, player_id, lock=''):

        plr_season_dict = self.retrieve_raw_season_data(player_id)

        plr_position = plr_season_dict.pop('position')

        for key in sorted(plr_season_dict.keys()):
            # keys are a tuple of season, season type, team count and team
            (season, season_type, team_season_cnt, team) = key
            season_data = plr_season_dict[key]

            if plr_position == 'G':
                pass
                # plr_season = NHLGoalieSeason(
                # player.player_id, season,
                #  season_type, team, team_season_cnt, season_data)
                # plr_season_db = NHLGoalieSeason.find(
                # player.player_id, team, season, season_type, team_season_cnt)
            else:
                plr_season = PlayerSeason(
                    player_id, season, season_type, team,
                    team_season_cnt, season_data)
                plr_season_db = PlayerSeason.find(
                    player_id, team, season, season_type, team_season_cnt)

            self.create_or_update_player_season(plr_season, plr_season_db)
