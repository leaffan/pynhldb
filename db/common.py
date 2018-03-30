#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.schema import MetaData
from sqlalchemy.ext.declarative import declarative_base

from utils import get_connection_string_from_config_file

cfg_src = os.path.join(os.path.dirname(__file__), "..", r"_config.yml")
conn_string = get_connection_string_from_config_file(cfg_src, 'db_conn')

Engine = create_engine(conn_string, echo=False, pool_size=5)
Session = sessionmaker(bind=Engine, expire_on_commit=False)
Base = declarative_base(metadata=MetaData(schema='nhl', bind=Engine))


@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
