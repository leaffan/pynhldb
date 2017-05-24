#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict

import requests
from lxml import html


BASE_URL = "http://www.hockey-reference.com"

GP_LEADERS_URL_TEMPLATE = (
    "http://www.hockey-reference.com/play-index/psl_finder.cgi?" +
    "c2stat=&c4stat=&c2comp=gt&is_playoffs=N&order_by_asc=&birthyear_max" +
    "=&birthyear_min=&c1comp=gt&year_min=&request=1&franch_id=&is_hof=&" +
    "birth_country=&match=combined&year_max=&c3comp=gt&season_end=-1&" +
    "is_active=&c3stat=&lg_id=NHL&order_by=games_played&season_start=1&" +
    "c1val=&threshhold=5&c3val=&c2val=&handed=&rookie=N&pos=S&describe_only" +
    "=&c1stat=&c4val=&age_min=0&c4comp=gt&age_max=99")


def get_links_names_games(url):
    """
    Retrieves names, number of games played and urls to individual pages for
    all players listed on ranking page with specified url.
    """
    req = requests.get(url)
    doc = html.fromstring(req.text)
    tds = doc.xpath("//tbody/tr/th[@scope='row']/following-sibling::td[1]")

    # retrieving relative urls to individual player pages
    links = [td.xpath("descendant::a/@href").pop(0) for td in tds]
    # retrieving player names
    names = [td.xpath("@csk").pop(0) for td in tds]
    # retrieving games played
    games = [int(td.xpath(
        "following-sibling::td[@data-stat='games_played']/text()").pop(
            0)) for td in tds]

    return links, names, games


def has_playoff_games(url):
    """
    Checks if a player has participated in playoff games.
    """
    req = requests.get(url)
    doc = html.fromstring(req.text)
    # if available playoff data is listed in a section with a special id
    playoff_section = doc.xpath(
        "//div[@class='section_heading']/span[@id='stats_playoffs_nhl_link']")
    if playoff_section:
        return True
    else:
        return False


def retrieve_seasons_and_teams(url):
    """
    Retrieves seasons and teams for a single player.
    """
    req = requests.get(url)
    doc = html.fromstring(req.text)
    teams = doc.xpath(
        "//table[@id='stats_basic_nhl' or @id='stats_basic_plus_nhl']" +
        "/tbody/tr/td[2]/a/text()")
    seasons = doc.xpath(
        "//table[@id='stats_basic_nhl' or @id='stats_basic_plus_nhl']" +
        "/tbody/tr/th[@data-stat='season']/text()")

    teams = list(OrderedDict.fromkeys(teams).keys())
    seasons = [
        int(seasons[0].split("-")[0]), int(seasons[-1].split("-")[0]) + 1]

    return teams, seasons


if __name__ == '__main__':

    result = list()

    for offset in range(2200, 2400, 200):
        url = GP_LEADERS_URL_TEMPLATE
        if offset:
            url = "".join((url, "&offset=%d" % offset))
        print(url)
        links, names, games = get_links_names_games(url)

        i = 0

        for link, name, games_played in zip(links, names, games):
            i += 1
            name = "%s" % " ".join(name.split(",")[::-1])
            print(name, end='')  # noqa: E999
            plr_url = "".join((BASE_URL, link))
            if not has_playoff_games(plr_url):
                print(": no playoff games")
                teams, seasons = retrieve_seasons_and_teams(plr_url)
                result.append((
                    name, str(games_played),
                    "-".join([str(s) for s in seasons]), ", ".join(teams)))
            else:
                print()
            # if i == 5:
            #     break

    open(r"d:\result.txt", "w").write(
        "\n".join(["\t".join(r) for r in result]))
