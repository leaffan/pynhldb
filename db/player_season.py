#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import timedelta

from sqlalchemy import and_

from .common import Base, session_scope


class PlayerSeason(Base):
    __tablename__ = 'player_seasons'
    __autoload__ = True

    STD_STATS = [
        'games_played', 'goals', 'assists', 'points',
        'plus_minus', 'pim', 'ppg', 'shg', 'gwg', 'shots']

    JSON_DB_MAPPING = {
        "timeOnIce": "toi",
        "assists": "assists",
        "goals": "goals",
        "pim": "pim",
        "shots": "shots",
        "games": "games_played",
        "hits": "hits",
        "powerPlayGoals": "ppg",
        "powerPlayPoints": "pp_pts",
        "powerPlayTimeOnIce": "pp_toi",
        "evenTimeOnIce": "ev_toi",
        "faceOffPct": "faceoff_pctg",
        "shotPct": "pctg",
        "gameWinningGoals": "gwg",
        "overTimeGoals": "otg",
        "shortHandedGoals": "shg",
        "shortHandedPoints": "sh_pts",
        "shortHandedTimeOnIce": "sh_toi",
        "blocked": "blocks",
        "plusMinus": "plus_minus",
        "points": "points",
        "shifts": "shifts",
        }

    INTERVAL_ATTRS = ["toi", "ev_toi", "pp_toi", "sh_toi"]

    def __init__(self, player_id, season, season_type, team, season_team_sequence, season_data):

        self.player_id = player_id
        self.season = season
        self.season_type = season_type
        self.season_team_sequence = season_team_sequence
        self.team_id = team.team_id

        for json_key in self.JSON_DB_MAPPING:
            if json_key in season_data.keys():
                try:
                    # creating actual time intervals for time-on-ice items
                    if self.JSON_DB_MAPPING[json_key] in self.INTERVAL_ATTRS:
                        minutes, seconds = [
                            int(x) for x in season_data[json_key].split(":")]
                        value = timedelta(minutes=minutes, seconds=seconds)
                    # all other items are already suitably
                    # stored in the json struct
                    else:
                        value = season_data[json_key]
                    setattr(self, self.JSON_DB_MAPPING[json_key], value)
                except:
                    print(
                        "Unable to retrieve %s from season data" %
                        self.JSON_DB_MAPPING[json_key])
                    # logger.warn(
                    # "Unable to retrieve %s from season data" %
                    # self.PLAYER_STATS_MAP[key])
        else:
            self.calculate_pctg()

    def calculate_pctg(self):
        if self.shots:
            self.pctg = round((float(self.goals) / float(self.shots)) * 100, 4)
        elif self.shots is None:
            self.pctg = None
        else:
            self.pctg = round(0., 2)

    @classmethod
    def find(self, player_id, team, season, season_type, season_team_sequence):
        with session_scope() as session:
            try:
                player_season = session.query(PlayerSeason).filter(
                    and_(
                        PlayerSeason.player_id == player_id,
                        PlayerSeason.season == season,
                        PlayerSeason.team_id == team.team_id,
                        PlayerSeason.season_type == season_type,
                        PlayerSeason.season_team_sequence == season_team_sequence
                    )
                ).one()
            except:
                player_season = None
            return player_season

    def update(self, other):
        for attr in self.JSON_DB_MAPPING.values():
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        else:
            self.calculate_pctg()
