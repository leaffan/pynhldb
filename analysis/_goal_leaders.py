#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import json

import requests
from lxml import html


logger = logging.getLogger(__name__)
SEASON_URL_TEMPLATE = "http://www.hockey-reference.com/leagues/NHL_%d.html"
CAREER_GOAL_LEADERS_URL = "http://www.hockey-reference.com/leaders/goals_career.html"


def retrieve_yearly_leaders(start_season=1917, end_season=2016):
    """
    Retrieves yearly NHL goal-scoring leaders.
    """
    yearly_leaders = set()

    # retrieving leading goal scorers for each NHL first
    for year in range(start_season, end_season)[:]:

        # skipping season completely lost to a lockout
        if year == 2004:
            continue

        season = "%d-%s" % (year, str(year + 1)[-2:])
        logger.info("+ Retrieving top goal scorers for season %s:" % season)

        # retrieving raw html data and parsing it
        url = SEASON_URL_TEMPLATE % (year + 1)
        r = requests.get(url)
        doc = html.fromstring(r.text)

        # the stuff we're interested in is hidden in comments
        comments = doc.xpath("//comment()")

        for comment in comments:
            # removing comment markup
            sub = html.fromstring(str(comment)[3:-3])
            if not sub.xpath("//table/caption/text()"):
                continue
            if sub.xpath("//table/caption/text()")[0] == "Goals":
                leaders = sub
                break

        # retrieving five best goalscorers in current season as list
        five_goal_leaders = leaders.xpath(
            "//div[@id='leaders_goals']/table/tr/td[@class='who']/a")
        # adding name and link to player page to goalscorer dictionary
        for leader in five_goal_leaders:
            logger.info("\t+ %s" % leader.xpath("text()")[0])
            yearly_leaders.add(
                (leader.xpath("@href")[0], leader.xpath("text()")[0]))

    return yearly_leaders


def retrieve_career_leaders(min_goals=350):
    """
    Retrieves NHL career goal scoring leaders with at least the number of 
    specified goals.
    """
    career_leaders = set()

    r = requests.get(CAREER_GOAL_LEADERS_URL)
    doc = html.fromstring(r.text)

    logger.info(
        "+ Registering players as NHL career goal scoring leaders:")

    # retrieving goal scorers with more than 300 career goals
    for leader_row in doc.xpath("//table[@id='stats_career_NHL']/tbody/tr"):

        goals = int(leader_row.xpath(
            "td[4]/text()")[0])

        # adding name and link to player page if goal total is greater or
        # equal the defined amount of minimum goals 
        if goals >= min_goals:
            plr_name = leader_row.xpath("td//a/text()")[0]
            logger.info("\t+ %s (%d career goals)" % (plr_name, goals))
            career_leaders.add((
                leader_row.xpath("td//a/@href")[0], plr_name))

    return career_leaders


if __name__ == '__main__':

    yearly_leaders = retrieve_yearly_leaders()
    career_leaders = retrieve_career_leaders(300)

    goal_leaders = yearly_leaders.union(career_leaders)

    open(r"goal_leaders.json", 'w').write(
        json.dumps(list(goal_leaders), sort_keys=True, indent=2))
