#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse

from analysis._goals_per_game import retrieve_goals_per_season
from analysis._goals_per_game import calculate_adjustment_factors
from analysis._goal_leaders import retrieve_career_leaders
from analysis._goal_leaders import retrieve_yearly_top
from analysis._adjust_goals import retrieve_and_adjust_goal_totals

from utils import prepare_logging
prepare_logging(log_types=['screen'])

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Adjusting individual goal scoring totals in dependance" +
                    "of league-wide scoring rate.")
    parser.add_argument(
        'steps',
        metavar='processing_steps',
        help='Processing step(s) to conduct.',
        choices=['1', '2', '3', 'all'])
    # TODO: add arguments for goal scoring leader retrieval, i.e. maximum top
    # position threshold or minimum career season total

    args = parser.parse_args()
    setup_steps = args.steps

    goals_per_season_path = os.path.join(
        "analysis", "goals_per_season.json")
    goal_leaders_path = os.path.join(
        "analysis", "career_goal_leaders.json")
    adjusted_goal_data_path = os.path.join(
        "analysis", "adjusted_goal_data.json")

    # retrieving goals per season and season adjustment factors
    if setup_steps in ['1', 'all']:
        season_data = retrieve_goals_per_season()
        calculate_adjustment_factors(season_data)

        open(goals_per_season_path, 'w').write(
            json.dumps(season_data, sort_keys=True, indent=2))

    # retrieving goal scoring leaders
    if setup_steps in ['2', 'all']:
        career_goal_leaders = list()
        yearly_top = list()
        # retrieving all players with at least 300 career goals
        career_goal_leaders = retrieve_career_leaders(300)
        # retrieving top five goalscorers per season
        yearly_top = retrieve_yearly_top(5)

        # retrieving urls to player pages for goal-scoring career leaders
        career_leaders_urls = [d['url'] for d in career_goal_leaders]
        # creating new list of all goal-scoring leaders
        goal_leaders = career_goal_leaders
        # adding goal-scoring per season leaders to list of all goal-scoring
        # leaders if they are not yet a part of it
        for yearly_leader in yearly_top:
            if yearly_leader['url'] not in career_leaders_urls:
                goal_leaders.append(yearly_leader)

        open(goal_leaders_path, 'w').write(
            json.dumps(goal_leaders, indent=2))

    # adjusting goal scoring totals according to goals scored per season
    if setup_steps in ['3', 'all']:
        adjusted_goal_data = retrieve_and_adjust_goal_totals(
            goal_leaders_path, goals_per_season_path)

        open(adjusted_goal_data_path, 'w').write(
            json.dumps(adjusted_goal_data, sort_keys=True, indent=2))
