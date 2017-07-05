#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urllib.parse import urlparse
from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import requests

from lxml import html

from utils import remove_non_ascii_chars

# base url for eliteprospects.com
BASE_URL = "http://www.eliteprospects.com"
# url template for draft overview pages at eliteprospects.com
DRAFT_URL_TEMPLATE = "draft.php?year=%d"
# maximum worker count
MAX_WORKERS = 4
# named tuple to contain basic player information
Player = namedtuple(
    'Player', 'first_name last_name date_of_birth alt_last_name')


def retrieve_drafted_players_with_dobs(draft_year):
    """
    Retrieves basic player data (first name, last name, date of birth,
    alternate last name) from all player pages in the specified list.
    """
    # retrieving links to pages of all drafted players first
    player_urls = retrieve_drafted_player_links(draft_year)
    # setting up target list
    players_with_dobs = list()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as processes:
        future_tasks = {
            processes.submit(
                get_player_with_dob, url): url for url in player_urls[:]}
        for future in as_completed(future_tasks):
            try:
                # TODO: think of something to do with the result here
                result = future.result()
                if result is not None:
                    players_with_dobs.append(result)
            except Exception as e:
                print
                print("Conccurrent task generated an exception: %s" % e)

    return players_with_dobs


def get_player_with_dob(url):
    """
    Retrieves single player along with date of birth.
    """
    req = requests.get(url)
    print("+ Retrieving player information from %s" % url)
    doc = html.fromstring(req.text)

    # retrieving birthdate url that contains all necessary information in
    # granular form, i.e. <a href="birthdate.php?Birthdate=1998-04-19&amp;
    # Firstname=Patrik&amp;Lastname=Laine">1998-04-19</a>
    dob_url = doc.xpath("//a[starts-with(@href, 'birthdate')]/@href")
    if not dob_url:
        return
    dob_url = dob_url.pop(0)
    # retrieving player information from retrieved url
    dob, first_name, last_name = get_player_details_from_url(dob_url)

    # retrieving alternate last name (if applicable)
    alt_last_name = ''
    aka = doc.xpath("//font[starts-with(text(), 'a.k.a.')]/text()")
    if aka:
        aka = aka.pop(0).replace("a.k.a.", "").replace('"', "").strip()
        # retrieving all available alternate names
        akas = [a.strip() for a in aka.split(",")]
        akas = [a.replace(first_name, "").strip() for a in akas]
        # using only first alternate last name
        # TODO: use all alternate names
        aka = akas[0]
        if aka != last_name:
            alt_last_name = aka

    # adding current player to list dictionary of players w/ date of births
    return Player(
        remove_non_ascii_chars(first_name),
        remove_non_ascii_chars(last_name),
        dob, alt_last_name)


def retrieve_drafted_player_links(draft_year):
    """
    Retrieves links to player pages for all players drafted in the specified
    draft year.
    """
    url = "/".join((BASE_URL, DRAFT_URL_TEMPLATE % draft_year))
    req = requests.get(url)
    doc = html.fromstring(req.text)

    print(
        "+ Retrieving urls to pages of each player drafted in %d" % draft_year)

    # stub links to player pages are present at the specified position in
    # the main table
    return ["/".join((BASE_URL, link)) for link in doc.xpath(
        "//tr[@bordercolor='#FFFFFF']/td[3]/a/@href")]


def get_player_details_from_url(dob_url):
    """
    Gets player details, i.e. first name, last name and date of birth, from
    specifield url.
    """
    # exploding url into its components
    url_comps = urlparse(dob_url)
    # retrieving player details by exploding each part of the url's
    # query component
    dob, first_name, last_name = [
        comp.split("=")[-1] for comp in url_comps.query.split("&")]
    return dob, first_name, last_name
