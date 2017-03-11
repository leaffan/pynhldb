#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base


class GoalieGame(Base):
    __tablename__ = 'goalie_games'
    __autoload__ = True

    STANDARD_ATTRS = [
        "position", "no", "goals", "assists", "primary_assists",
        "secondary_assists", "points", "plus_minus", "penalties", "pim",
        "toi_overall", "toi_pp", "toi_sh", "toi_ev", "avg_shift", "no_shifts",
        "shots_on_goal", "shots_blocked", "shots_missed", "hits",
        "giveaways", "takeaways", "blocks", "faceoffs_won", "faceoffs_lost",
        "on_ice_shots_on_goal", "on_ice_shots_blocked", "on_ice_shots_missed"
    ]
