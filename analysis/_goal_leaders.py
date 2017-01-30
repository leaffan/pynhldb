#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

import requests
from lxml import html


SEASON_URL_TEMPLATE = "http://www.hockey-reference.com/leagues/NHL_%d.html"
CAREER_GOAL_LEADERS_URL = "http://www.hockey-reference.com/leaders/goals_career.html"


def retrieve_yearly_leaders():
    """
    Retrieves yearly NHL goal-scoring leaders.
    """
    yearly_leaders = set()

    # retrieving leading goal scorers for each NHL first
    for year in range(1918, 2017)[:]:

        # skipping season completely lost to a lockout
        if year == 2005:
            continue

        season = "%d-%s" % (year - 1, str(year)[-2:])
        print("+ Retrieving top goal scorers for season %s" % season)

        # retrieving raw html data and parsing it
        url = SEASON_URL_TEMPLATE % year
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
            print("\t%s" % leader.xpath("text()")[0])
            yearly_leaders.add(
                (leader.xpath("@href")[0], leader.xpath("text()")[0]))

    return yearly_leaders


def retrieve_career_leaders(min_goals):
    """
    Retrieves NHL career goal scoring leaders with at least the number of 
    specified goals.
    """
    career_leaders = set()

    r = requests.get(CAREER_GOAL_LEADERS_URL)
    doc = html.fromstring(r.text)

    # retrieving goal scorers with more than 300 career goals
    for leader_row in doc.xpath("//table[@id='stats_career_NHL']/tbody/tr"):

        goals = int(leader_row.xpath(
            "td[4]/text()")[0])

        if goals >= min_goals:
            print(leader_row.xpath("td//a/text()")[0])
            career_leaders.add((
                leader_row.xpath("td//a/@href")[0],
                leader_row.xpath("td//a/text()")[0]))

    return career_leaders


if __name__ == '__main__':

    yearly_leaders = retrieve_yearly_leaders()
    career_leaders = retrieve_career_leaders(300)

    goal_leaders = yearly_leaders.union(career_leaders)

    open(r"nhl_goals_leaders.json", 'w').write(
        json.dumps(list(goal_leaders), sort_keys=True, indent=2))
