#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from analysis._goals_per_game import retrieve_goals_per_season
from analysis._goals_per_game import calculate_adjustment_factors
from analysis._goal_leaders import retrieve_career_leaders
from analysis._goal_leaders import retrieve_yearly_leaders
from analysis._adjust_goals import retrieve_and_adjust_goal_totals

from utils import prepare_logging
prepare_logging(log_types=['screen'])

if __name__ == '__main__':

    goals_per_season_path = os.path.join(
        "analysis", "goals_per_season.json")
    career_goal_leaders_path = os.path.join(
        "analysis", "career_goal_leaders.json")
    adjusted_goal_data_path = os.path.join(
        "analysis", "adjusted_goal_data.json")

    # retrieving goals per season and season adjustment factors
    season_data = retrieve_goals_per_season(1917, 2016)
    calculate_adjustment_factors(season_data)

    open(goals_per_season_path, 'w').write(
        json.dumps(season_data, sort_keys=True, indent=2))

    # retrieving goal scoring leaders
    career_goal_leaders = retrieve_career_leaders(300)
    # yearly_leaders = retrieve_yearly_leaders(1917, 1919)

    open(career_goal_leaders_path, 'w').write(
        json.dumps(list(career_goal_leaders), indent=2))

    # adjusting goal scoring totals according to goals scored per season
    adjusted_goal_data = retrieve_and_adjust_goal_totals(
        career_goal_leaders_path, goals_per_season_path)

    open(adjusted_goal_data_path, 'w').write(
        json.dumps(adjusted_goal_data, sort_keys=True, indent=2))
