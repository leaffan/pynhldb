#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import timedelta

from sqlalchemy import and_

from .common import Base, session_scope
from .team import Team


class GoalieSeason(Base):
    __tablename__ = 'goalie_seasons'
    __autoload__ = True
    __human_readable__ = 'goalie season'

    # statistics items mapped from original json struct to database attributes
    JSON_DB_MAPPING = {
        "timeOnIce": "toi",
        "games": "games_played",
        "gamesStarted": "games_started",
        "ot": "otl",
        "shutouts": "so",
        "ties": "ties",
        "wins": "wins",
        "losses": "losses",
        "saves": "saves",
        "powerPlaySaves": "pp_saves",
        "shortHandedSaves": "sh_saves",
        "evenSaves": "even_saves",
        "shortHandedShots": "sh_sa",
        "evenShots": "even_sa",
        "powerPlayShots": "pp_sa",
        "savePercentage": "save_pctg",
        "goalAgainstAverage": "gaa",
        "shotsAgainst": "sa",
        "goalsAgainst": "ga",
        }

    # attributes that are to be treated as time intervals
    INTERVAL_ATTRS = ["toi"]

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
        else:
            self.calculate_pctg()

    def calculate_pctg(self):
        """
        Calculates save percentage and goals against average
        for current goalie season.
        """
        # converting interval to full minutes
        self.minutes = self.toi.total_seconds() // 60
        if self.minutes:
            self.gaa = round(self.ga * 60. / self.minutes, 2)
        else:
            self.gaa = None
        if self.sa:
            self.save_pctg = round((self.sa - self.ga) / float(self.sa), 3)
        else:
            self.save_pctg = None

    @classmethod
    def find(self, player_id, team, season, season_type, season_team_sequence):
        with session_scope() as session:
            try:
                goalie_season = session.query(GoalieSeason).filter(
                    and_(
                        GoalieSeason.player_id == player_id,
                        GoalieSeason.season == season,
                        GoalieSeason.team_id == team.team_id,
                        GoalieSeason.season_type == season_type,
                        GoalieSeason.season_team_sequence ==
                        season_team_sequence
                    )
                ).one()
            except:
                goalie_season = None
            return goalie_season

    @classmethod
    def find_all(self, player_id):
        with session_scope() as session:
            try:
                goalie_seasons = session.query(GoalieSeason).filter(
                    GoalieSeason.player_id == player_id,
                ).all()
            except:
                goalie_seasons = None
            return goalie_seasons

    def update(self, other):
        for attr in self.JSON_DB_MAPPING.values():
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        else:
            self.calculate_pctg()

    def __eq__(self, other):
        return (
            (self.games_played, self.wins, self.losses, self.ties,
             self.otl, self.so, self.ga, self.sa, str(self.save_pctg),
             str(self.gaa), self.minutes, self.games_started, self.saves,
             self.even_sa, self.even_saves, self.pp_sa, self.pp_saves,
             self.sh_sa, self.sh_saves, self.toi) ==
            (other.games_played, other.wins, other.losses, other.ties,
             other.otl, other.so, other.ga, other.sa, str(other.save_pctg),
             str(other.gaa), other.minutes, other.games_started, other.saves,
             other.even_sa, other.even_saves, other.pp_sa, other.pp_saves,
             other.sh_sa, other.sh_saves, other.toi))

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
        if self.save_pctg is None:
            save_pctg = round(0., 3)
        else:
            save_pctg = self.save_pctg

        if self.minutes is None:
            minutes = 0
        else:
            minutes = self.minutes

        if self.gaa is None:
            gaa = 0.0
        else:
            gaa = self.gaa

        if self.season_type == 'RS':
            if self.ties is None:
                ties_otl = self.otl
            else:
                ties_otl = self.ties
            return "%d %-25s %2d %2d %2d %2d %3d %4d %1.3f %5d %1.2f %2d" % (
                self.season, Team.find_by_id(self.team_id), self.games_played,
                self.wins, self.losses, ties_otl, self.ga, self.sa, save_pctg,
                minutes, gaa, self.so)
        else:
            return "%d %-25s %2d %2d %2d %6d %4d %1.3f %5d %1.2f %2d" % (
                self.season, Team.find_by_id(self.team_id), self.games_played,
                self.wins, self.losses, self.ga, self.sa, save_pctg,
                minutes, gaa, self.so)
