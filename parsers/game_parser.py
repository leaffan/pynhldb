#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re


class GameParser():

    # defining time zone information
    TZINFO = {'CET':   3600, 'CEST':    7200,
              'EET':   7200, 'EETDST': 10800,
              'EDT': -14400, 'EST': -18000,
              'CDT': -18000, 'CST': -21600,
              'MDT': -21600, 'MST': -25200,
              'PDT': -25200, 'PST': -28800,
              'BST':   3600}

    ATTENDANCE_AT_VENUE_REGEX = re.compile("\s(@|at)\s")
