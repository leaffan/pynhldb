#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urllib.parse import urlparse
from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import requests

from lxml import html

from utils import remove_non_ascii_chars

# base url for eliteprospects.com
BASE_URL = "https://www.eliteprospects.com"
# url template for draft overview pages at eliteprospects.com
DRAFT_URL_TEMPLATE = "draft/nhl-entry-draft/%d"
# maximum worker count
MAX_WORKERS = 8
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

    # retrieving date of birth
    dob_url = doc.xpath("//a[contains(@href, '?dob=')]/@href").pop()
    url_comps = urlparse(dob_url)
    for item in url_comps.query.split('&'):
        if 'dob' in item:
            dob = item.split("=")[-1]

    # retrieving first and last name
    title = doc.xpath("//title/text()").pop()
    full_name = title.replace("- Elite Prospects", "").replace(" - Stats, Contract, Salary & More", "").strip()
    first_name, last_name = full_name.split(maxsplit=1)

    # retrieving alternate last name (if applicable)
    alt_last_name = get_alternate_last_name(doc, first_name, last_name)

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
        "+ Retrieving urls of Eliteprospects profiles " +
        "for each player drafted in %d" % draft_year)

    # links to player pages are present at the specified position in the
    # main table
    return doc.xpath(
        "//table[@data-sort-ajax-container='#drafted-players']//tbody//td" +
        "[@class='player']//span[@class='txt-blue']/a/@href")


def get_alternate_last_name(doc, first_name, last_name):
    """
    If applicable, retrieves alternate last name from specified player page
    and given player's first and last names.
    """
    alt_last_name = ''
    aka_element = doc.xpath("//div[@class='ep-entity-header__alternative-name']/text()")
    if aka_element:
        aka = aka_element.pop().strip().replace("a.k.a.", "").replace('"', "").strip()
        # retrieving all available alternate names
        akas = [a.strip() for a in aka.split(",")]
        tmp_alt_last_names = list()
        for aka in akas:
            # trying to remove already known first name
            aka_wo_first_name = aka.replace(first_name, "").strip()
            # splitting remaining alternate name
            tokens = aka_wo_first_name.split()
            # if known first name was actually removed, the rest is
            # the alternate last name
            # if we above just had a first name removed that was the short form
            # of a longer one, i.e. Nicklaus Perbix - Nick => laus Perbix, the
            # remaining part o/c does not represent an alternate last name
            if aka != aka_wo_first_name and not aka_wo_first_name[0].islower():
                tmp_alt_last_names.append(aka_wo_first_name)
            # if there's just one token after the split and first letters in
            # split result and original name match: this token is the alternate
            # last name
            elif len(tokens) == 1:
                if tokens[0][0].lower() == last_name.lower()[0]:
                    tmp_alt_last_names.append(tokens[0])
            # if there are two tokens after the split: first one is alternate
            # first, second one alternate last name
            elif len(tokens) == 2:
                tmp_alt_last_names.append(tokens[-1])
            else:
                # TODO: logger warning
                print(
                    "Unable to retrieve alternate last " +
                    "name for %s %s from: %s" % (first_name, last_name, aka))
        # using only first found alternate last name
        # TODO: use all alternate names
        if tmp_alt_last_names and tmp_alt_last_names[0] != last_name:
            alt_last_name = tmp_alt_last_names[0]

    return alt_last_name
