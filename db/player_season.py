#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from sqlalchemy import and_

from .common import Base, session_scope
from .team import Team

logger = logging.getLogger(__name__)


class PlayerSeason(Base):
    __tablename__ = 'player_seasons'
    __autoload__ = True

    HUMAN_READABLE = 'player season'

    # statistics items mapped from original json struct to database attributes
    JSON_DB_MAPPING = {
        "timeOnIce": "toi",
        "assists": "assists",
        "goals": "goals",
        "pim": "pim",
        "shots": "shots",
        # "games": "games_played",
        "gamesPlayed": "games_played",
        # "hits": "hits",
        "powerPlayGoals": "ppg",
        "powerPlayPoints": "pp_pts",
        # "powerPlayTimeOnIce": "pp_toi",
        # "evenTimeOnIce": "ev_toi",
        # "faceOffPct": "faceoff_pctg",
        "faceoffWinningPctg": "faceoff_pctg",
        # "shotPct": "pctg",
        "shootingPctg": "pctg",
        "gameWinningGoals": "gwg",
        # "overTimeGoals": "otg",
        "otGoals": "otg",
        "shorthandedGoals": "shg",
        "shorthandedPoints": "sh_pts",
        # "shortHandedTimeOnIce": "sh_toi",
        # "blocked": "blocks",
        "plusMinus": "plus_minus",
        "points": "points",
        # "shifts": "shifts",
        }

    # attributes that are to be treated as time intervals
    INTERVAL_ATTRS = ["toi", "ev_toi", "pp_toi", "sh_toi"]

    def __init__(
            self, player_id, season, season_type,
            team, season_team_sequence, season_data):

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
                except Exception as e:
                    logger.warn(
                        "Unable to retrieve %s from season data" %
                        self.JSON_DB_MAPPING[json_key])
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
                        PlayerSeason.season_team_sequence ==
                        season_team_sequence
                    )
                ).one()
            except Exception as e:
                player_season = None
            return player_season

    @classmethod
    def find_all(self, player_id):
        with session_scope() as session:
            try:
                player_seasons = session.query(PlayerSeason).filter(
                    PlayerSeason.player_id == player_id,
                ).all()
            except Exception as e:
                player_seasons = None
            return player_seasons

    def update(self, other):
        for attr in self.JSON_DB_MAPPING.values():
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        else:
            self.calculate_pctg()

    def __eq__(self, other):
        return (
            (self.games_played, self.goals, self.assists, self.points,
             self.plus_minus, self.pim, self.ppg, self.shg, self.gwg,
             self.shots, self.pp_pts, self.sh_pts, self.otg, str(self.pctg),
             self.hits, self.blocks, self.shifts, str(self.faceoff_pctg),
             self.toi, self.ev_toi, self.pp_toi, self.sh_toi
             ) ==
            (other.games_played, other.goals, other.assists, other.points,
             other.plus_minus, other.pim, other.ppg, other.shg, other.gwg,
             other.shots, other.pp_pts, other.sh_pts, other.otg,
             str(other.pctg), other.hits, other.blocks, other.shifts,
             str(other.faceoff_pctg), other.toi, other.ev_toi, other.pp_toi,
             other.sh_toi
             ))

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if self.season_type == other.season_type:
            if self.season <= other.season:
                return True
            else:
                return False
        else:
            if self.season_type > other.season_type:
                return True
            else:
                return False

    def __gt__(self, other):
        return not self.__lt__(other)

    def __str__(self):
        if self.shots is None:
            shots = "-"
        else:
            shots = str(self.shots)

        if self.pctg is None:
            pctg = "-"
        else:
            pctg = str(round(self.pctg, 1))

        return "%d %-25s %2d %2d %2d %3d %3d %2d %2d %2d %3s %5s" % (
            self.season, Team.find_by_id(self.team_id),
            self.games_played, self.goals, self.assists, self.points,
            self.pim, self.ppg, self.shg, self.gwg, shots, pctg)
