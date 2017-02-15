#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import session_scope


def commit_db_item(self, db_item):
    with session_scope() as session:
        session.merge(db_item)
        session.commit()
