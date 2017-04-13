#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import requests
from lxml import html

logger = logging.getLogger(__name__)

HOCKEY_REF_PREFIX = "http://www.hockey-reference.com"
SEASON_URL_TEMPLATE = "".join((HOCKEY_REF_PREFIX, "/leagues/NHL_%d.html"))
CAREER_GOAL_LEADERS_URL = "".join(
    (HOCKEY_REF_PREFIX, "/leaders/goals_career.html"))


def retrieve_yearly_top(top=10, start_season=1917, end_season=2016):
    """
    Retrieves yearly top (maximum ten) goalscorers from single site.
    """
    url = "http://www.hockey-reference.com/leaders/goals_top_10.html"
    r = requests.get(url)
    doc = html.fromstring(r.text)

    yearly_top_goalscorers = list()
    processed_urls = set()

    for year in range(start_season, end_season + 1)[:]:
        if year == 2004:
            continue

        season = "%d-%s" % (year, str(year + 1)[-2:])
        logger.info(
            "+ Retrieving top %d goal scorers for season %s:" % (top, season))

        # table rows of interest for current season
        trs = doc.xpath("//div[@id='leaders_y%d']/table/tr" % (year + 1))

        # retrieving player ranks
        plr_ranks = [tr.xpath("td[@class='rank']")[0] for tr in trs]
        # retrieving player names
        plr_names = [tr.xpath(
            "td[@class='who']/a/descendant-or-self::text()")[0] for tr in trs]
        # retrieving links to player pages
        plr_urls = [tr.xpath("td[@class='who']/a/@href")[0] for tr in trs]

        for rank, name, url in zip(plr_ranks, plr_names, plr_urls):
            rank_txt = rank.xpath("text()")
            if rank_txt:
                rank = int(rank_txt.pop(0)[:-1])
                # breaking out of loop if current rank is *lower* than
                # target rank
                if rank > top:
                    break
            # skipping player if it was already registered
            if url in processed_urls:
                continue
            logger.info("\t+ %s" % name)
            # creating and populating single player dictionary
            single_player_dict = dict()
            single_player_dict['url'] = url
            single_player_dict['name'] = name
            single_player_dict['yearly_leader'] = True
            yearly_top_goalscorers.append(single_player_dict)
            processed_urls.add(url)

    return yearly_top_goalscorers


def retrieve_yearly_leaders(start_season=1917, end_season=2016):
    """
    Retrieves yearly NHL goal-scoring leaders (fixed at top 5, from multiple
    sites).
    This function is deprecated. Use the other one for top goalscorer retrieval
    per season.
    """
    yearly_leaders = list()
    processed_urls = set()

    # retrieving leading goal scorers for each NHL first
    for year in range(start_season, end_season + 1)[:]:

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
        # adding name and url to player page to goalscorer dictionary
        for leader in five_goal_leaders:
            url = leader.xpath("@href")[0]
            name = leader.xpath("text()")[0]
            # skipping player if it was already registered
            if url in processed_urls:
                continue
            logger.info("\t+ %s" % name)
            # creating and populating single player dictionary
            single_player_dict = dict()
            single_player_dict['url'] = url
            single_player_dict['name'] = name
            single_player_dict['yearly_leader'] = True
            yearly_leaders.append(single_player_dict)
            processed_urls.add(url)

    return yearly_leaders


def retrieve_career_leaders(min_goals=350):
    """
    Retrieves NHL career goal scoring leaders with at least the number of
    specified goals.
    """
    career_leaders = list()

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
            name = leader_row.xpath("td//a/text()")[0]
            url = leader_row.xpath("td//a/@href")[0]
            logger.info("\t+ %s (%d career goals)" % (name, goals))
            # creating and populating single player dictionary
            single_player_dict = dict()
            single_player_dict['url'] = url
            single_player_dict['name'] = name
            single_player_dict['yearly_leader'] = False
            career_leaders.append(single_player_dict)

    return career_leaders


if __name__ == '__main__':
    pass
