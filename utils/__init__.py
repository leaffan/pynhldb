#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
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
