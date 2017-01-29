#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from lxml import html


SEASON_URL_TEMPLATE = "http://www.hockey-reference.com/leagues/NHL_%d.html"
CAREER_GOAL_LEADERS_URL = "http://www.hockey-reference.com/leaders/goals_career.html"


season_goal_leaders = set()

for year in range(1918, 2017)[:0]:

    # skipping season completely lost to a lockout
    if year == 2005:
        continue

    season = "%d-%s" % (year - 1, str(year)[-2:])

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
        season_goal_leaders.add(
            (leader.xpath("@href")[0], leader.xpath("text()")[0]))

r = requests.get(CAREER_GOAL_LEADERS_URL)
doc = html.fromstring(r.text)



print(sorted(season_goal_leaders))
