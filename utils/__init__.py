#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import unicodedata
import logging
import logging.handlers
from datetime import timedelta, date

import yaml
from lxml import html, etree


def ordinal(n):
    return "%d%s" % (n, "tsnrhtdd"[(n/10 % 10 != 1)*(n % 10 < 4)*n % 10::4])


def remove_null_strings(list_of_strings):
    return [s for s in list_of_strings if s.strip()]


def retrieve_season(date_of_interest=None):
    """
    Identifies season based on month of given date, anything until June
    belongs to the season ending in the date's year, anything after
    June belongs to the season beginning in the date's year.
    NB: Seasons are identified by the year they're beginning in, even for
    those that are shortened, i.e. 2012/13.
    """
    if date_of_interest is None:
        date_of_interest = date.today()
    if date_of_interest.month < 7:
        season = date_of_interest.year - 1
    else:
        if date_of_interest.year == 2020:
            season = 2019
        else:
            season = date_of_interest.year

    return season


def reverse_num_situation(num_situation):
    """
    Returns opposing numerical situation for specified one.
    """
    if num_situation == 'PP':
        return 'SH'
    elif num_situation == 'SH':
        return 'PP'
    else:
        return num_situation


# request response function
def adjust_html_response(response):
    """
    Applies some modifications to the html source of the given HTTP
    response in order to alleviate later handling of the data.
    """
    # converting to document tree
    doc = html.document_fromstring(response.text)

    # stripping all script elements in order to remove javascripts
    etree.strip_elements(doc, "script")
    # stripping arbitraty xmlfile tag
    etree.strip_tags(doc, "xmlfile")

    # creating element to hold timestamp of last modification
    last_modified_element = etree.Element('p', id='last_modified')
    last_modified_element.text = response.headers.get('Last-Modified')

    # adding timestamp to document tree
    body = doc.xpath("body").pop(0)
    body.append(last_modified_element)

    # returning document tree dumped as string
    return etree.tostring(doc, method='html')


# unicode function
def remove_non_ascii_chars(s):
    """
    Removes non-ascii characters from specified (unicode) string.
    Basically following examples from http://bit.ly/2umENUv and
    http://bit.ly/2sFScdQ.
    """
    # latin-1 characters that don't have a unicode decomposition
    CHAR_REPLACE = {
        0xc6: u"AE",  # LATIN CAPITAL LETTER AE
        0xd0: u"D",   # LATIN CAPITAL LETTER ETH
        0xd8: u"O",   # LATIN CAPITAL LETTER O WITH STROKE
        0xde: u"Th",  # LATIN CAPITAL LETTER THORN
        0xdf: u"ss",  # LATIN SMALL LETTER SHARP S
        0xe6: u"ae",  # LATIN SMALL LETTER AE
        0xf0: u"d",   # LATIN SMALL LETTER ETH
        0xf8: u"o",   # LATIN SMALL LETTER O WITH STROKE
        0xfe: u"th",  # LATIN SMALL LETTER THORN
        }

    nfkd_form = unicodedata.normalize('NFKD', s)
    # decomposing unicode string
    decomposed = "".join(
        [char for char in nfkd_form if not unicodedata.combining(char)])
    # replacing non-decomposable non-ascii characters
    return "".join(
        [CHAR_REPLACE[ord(char)] if ord(
            char) in CHAR_REPLACE else char for char in decomposed])


# conversion functions
def str_to_timedelta(interval_as_str):
    """
    Converts a string time interval, i.e. '12:34', to an actual time interval.
    """
    try:
        m, s = [int(x) for x in interval_as_str.split(":")]
    except ValueError:
        m = 0
        s = 0
    return timedelta(0, m * 60 + s)


def feet_to_cm(feet, inches):
    """
    Converts feet and inches to centimeters.
    """
    if type(feet) is not int:
        feet = int(feet.replace("'", ""))
    if type(inches) is not int:
        inches = int(inches.replace('"', ''))
    return feet * 30.48 + inches * 2.54


def feet_to_m(feet, inches):
    """
    Converts feet and inches to meters.
    """
    cm = feet_to_cm(feet, inches)
    return cm / 100.


def lbs_to_kg(lbs):
    """
    Converts pounds to kilograms.
    """
    return lbs * 0.453592


def get_target_directory_from_config_file(cfg_src):
    """
    Gets download directory from specified section in
    a configuration file.
    """
    # reading complete configuration
    with open(cfg_src, 'r') as yml_file:
        cfg = yaml.safe_load(yml_file)

    try:
        tgt_dir = cfg['downloading']['tgt_dir']
    except KeyError as e:
        print(
            "Unable to retrieve parameter '%s' "
            "from configuration file." % e.args[0])
        return
    except Exception:
        print("Unable to read configuration file")
        return

    return tgt_dir


# utility function for database connection
def get_connection_string_from_config_file(cfg_src, db_cfg_key):
    """
    Gets connection parameters from specified section in
    a configuration file.
    """
    # reading complete configuration
    with open(cfg_src, 'r') as yml_file:
        cfg = yaml.safe_load(yml_file)

    # looking for specified connection name
    for connection_cfg in cfg['connections']:
        if db_cfg_key in connection_cfg:
            db_cfg = connection_cfg[db_cfg_key]

    # reading distinct configuration parameters
    try:
        db_engine = db_cfg['db_engine']
        user = db_cfg['user']
        password = db_cfg['password']
        host = db_cfg['host']
        port = db_cfg['port']
        database = db_cfg['database']
    except KeyError as e:
        print(
            "Unable to retrieve parameter '%s' "
            "from configuration file." % e.args[0])
        return
    except Exception:
        print("Unable to read configuration file")
        return

    # setting up connection string
    conn_string = "{0}://{1}:{2}@{3}:{4}/{5}".format(
        db_engine, user, password, host, port, database)

    return conn_string


# utility class and functions for logging purposes
# logging formatter
class WhitespaceRemovingFormatter(logging.Formatter):
    """
    Defines a special logging formatter that removes '+ ' from the beginning
    of the logged message.
    """
    REGEX = re.compile(R"^\+?\s")

    def format(self, record):
        record.msg = record.msg.strip()
        record.msg = re.sub(self.REGEX, "", record.msg)
        return super(WhitespaceRemovingFormatter, self).format(record)


def prepare_logging(log_types=['file', 'screen'], logdir=''):
    """
    Prepares logging for the specified channels, e.g. 'file' (a log file) and
    'screen' (the command line).
    """
    logging.getLogger("requests").setLevel(logging.WARNING)

    if not logdir:
        logdir = os.path.join(os.getenv("TEMP"), "log")

    if not os.path.isdir(logdir):
        os.makedirs(logdir)

    handlers = list()

    if 'screen' in log_types:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_formatter = logging.Formatter("%(message)s")
        stream_handler.setFormatter(stream_formatter)
        handlers.append(stream_handler)

    if 'file' in log_types:

        file_formatter = WhitespaceRemovingFormatter(
            "%(asctime)s.%(msecs)03d %(thread)5d " +
            "%(name)-35s %(levelname)-8s %(message)s",
            datefmt="%y-%m-%d %H:%M:%S")

        debug_log = os.path.join(logdir, 'pynhldb_debug.log')
        file_debug_handler = logging.handlers.TimedRotatingFileHandler(
            debug_log, when='midnight', interval=1)
        file_debug_handler.setFormatter(file_formatter)
        file_debug_handler.setLevel(logging.DEBUG)
        handlers.append(file_debug_handler)

        info_log = os.path.join(logdir, 'pynhldb_info.log')
        file_info_handler = logging.handlers.TimedRotatingFileHandler(
            info_log, when='midnight', interval=1)
        file_info_handler.setFormatter(file_formatter)
        file_info_handler.setLevel(logging.INFO)
        handlers.append(file_info_handler)

        warn_log = os.path.join(logdir, 'pynhldb_warn.log')
        file_warn_handler = logging.handlers.TimedRotatingFileHandler(
            warn_log, when='midnight', interval=1)
        file_warn_handler.setFormatter(file_formatter)
        file_warn_handler.setLevel(logging.WARN)
        handlers.append(file_warn_handler)

        logging.Formatter.formatTime

        error_log = os.path.join(logdir, 'pynhldb_error.log')
        file_error_handler = logging.handlers.TimedRotatingFileHandler(
            error_log, when='midnight', interval=1)
        file_error_handler.setFormatter(file_formatter)
        file_error_handler.setLevel(logging.ERROR)
        handlers.append(file_error_handler)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    for handler in handlers:
        logger.addHandler(handler)


def compare_json_data(source_data_a, source_data_b):
    """
    Compares specified JSON structures by structure and contents,
    cf. http://bit.ly/2A2yMTA.
    """
    def compare(data_a, data_b):
        # comparing lists
        if (type(data_a) is list):
            # is [data_b] a list and of same length as [data_a]?
            if (
                (type(data_b) != list) or
                (len(data_a) != len(data_b))
            ):
                return False

            # iterate over list items
            for list_index, list_item in enumerate(data_a):
                # compare [data_a] list item against [data_b] at index
                if (not compare(list_item, data_b[list_index])):
                    return False

            # list identical
            return True

        # comparing dictionaries
        if (type(data_a) is dict):
            # is [data_b] a dictionary?
            if (type(data_b) != dict):
                return False

            # iterate over dictionary keys
            for dict_key, dict_value in data_a.items():
                # key exists in [data_b] dictionary, and same value?
                if (
                    (dict_key not in data_b) or
                    (not compare(dict_value, data_b[dict_key]))
                ):
                    return False

            # dictionary identical
            return True

        # simple value - compare both value and type for equality
        return (
            (data_a == data_b) and
            (type(data_a) is type(data_b))
        )

    # compare a to b, then b to a
    return (
        compare(source_data_a, source_data_b) and
        compare(source_data_b, source_data_a)
    )


def order_dict(dictionary):
    result = {}
    for k, v in sorted(dictionary.items()):
        if isinstance(v, dict):
            result[k] = order_dict(v)
        else:
            result[k] = v
    return result
