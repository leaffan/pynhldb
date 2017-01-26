#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import logging
import logging.handlers
import os
import re
from configparser import NoOptionError, NoSectionError


def get_connection_string_from_config_file(cfg_src, section):
    """
    Gets connection parameters from specified section in
    a configuration file.
    """
    cfg_parser = configparser.ConfigParser()
    cfg_parser.read(cfg_src)

    try:
        db_engine = cfg_parser.get(section, 'db_engine')
        user = cfg_parser.get(section, 'user')
        password = cfg_parser.get(section, 'password')
        host = cfg_parser.get(section, 'host')
        port = cfg_parser.get(section, 'port')
        database = cfg_parser.get(section, 'database')
    except NoOptionError as e:
        print(e)
        return
    except NoSectionError as e:
        print(e)
        return
    except KeyError as e:
        print(
            "Unable to retrieve parameter '%s' "
            "from configuration file." % e.args[0])
        return

    conn_string = "{0}://{1}:{2}@{3}:{4}/{5}".format(
        db_engine, user, password, host, port, database)

    return conn_string


def feet_to_cm(feet, inches):
    u"""
    Converts feet and inches to centimeters.
    """
    if type(feet) is not int:
        feet = int(feet.replace("'", ""))
    if type(inches) is not int:
        inches = int(inches.replace('"', ''))
    return feet * 30.48 + inches * 2.54


class WhitespaceRemovingFormatter(logging.Formatter):

    REGEX = re.compile("^\+?\s")

    def format(self, record):
        record.msg = record.msg.strip()
        record.msg = re.sub(self.REGEX, "", record.msg)
        return super(WhitespaceRemovingFormatter, self).format(record)


def prepare_logging(log_types=['file', 'screen'], logdir=''):

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

        file_formatter = logging.Formatter(
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
