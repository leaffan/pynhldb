#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

src = r"transactions_2015.txt"
keywords_src = r"transaction_keywords.txt"

# abbreviations for month names
months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May' 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# regular expression to filter punctuation marks and brackets
notation_regex = re.compile(";|,|\.|\(|\)")

# common English words to ignore
common_words = [
    'a', 'after', 'an', 'and', 'are', 'as', 'at', 'back', 'be', 'been', 'both',
    'by', 'do', 'does', 'down', 'during', 'either', 'for', 'from', 'had',
    'has', 'him', 'his', 'if', 'in', 'is', 'it', 'not', 'of', 'off', 'on',
    'one', 'only', 'or', 'other', 'out', 'some', 'than', 'that', 'the',
    'their', 'they', 'to', 'until', 'up', 'via', 'was', 'who', 'with',
    'within',
]

# reading common hockey transaction keywords to ignore
keywords = [
    line.strip() for line in open(keywords_src).readlines() if not line.strip(
        ).startswith("#")]


def find_unusual_terms(lines):

    lowers = set()
    uppers = set()

    for line in lines[:]:
        # splitting up each line at white spaces, removing punctuation marks or
        # brackets
        tokens = [re.sub(notation_regex, "", token) for token in line.split()]
        to_lower = False
        # checking each token
        for token in tokens:
            # ignoring digits, month abbreviations or common words
            if token.isdigit() or token in months or token in common_words:
                continue
            # ignoring tokens starting with a digit, e.g. *63rd*
            if token and token[0].isdigit():
                continue
            if to_lower:
                token = token.lower()
                to_lower = False
            # making sure each beginning of a singular transaction notice is
            # converted to lower case, e.g. *Acquired* -> *acquired*
            if token.endswith(":"):
                to_lower = True
                token = token[:-1]
            if token in keywords:
                continue
            # adding upper case tokens to corresponding set
            if token and token[0].isupper():
                uppers.add(token)
            # adding lower case tokens to corresponding set
            if token and token[0].islower():
                lowers.add(token)

    return lowers, uppers


def locate_occurrences(unusual_terms):
    """
    Locates all occurrences of each unusual term in original dataset.
    """
    # re-reading original data
    orig_lines = open(src).readlines()
    # creating regular expression pattern to prepend and append to the
    # actual term
    pref_suff_pattern = "(" + "|".join((notation_regex.pattern, "/", "\s)"))

    for item in sorted(unusual_terms):
        print("+ Unknown term found: %s" % item)
        # creating regular expression to find unusual item in original data
        item_regex = re.compile("%s%s%s" % (
            pref_suff_pattern, item, pref_suff_pattern))
        for occurrence in list(filter(item_regex.search, orig_lines)):
            idx = orig_lines.index(occurrence)
            print("\t+ Line %d: *%s*" % (idx + 1, orig_lines[idx].strip()))


if __name__ == '__main__':

    lines = [line.strip().replace("/", " ") for line in open(src).readlines()]
    lowers, uppers = find_unusual_terms(lines)
    locate_occurrences(lowers)

    open(r"uppers.txt", 'w').write("\n".join(list(sorted(uppers))))
