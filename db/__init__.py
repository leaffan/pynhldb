#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import session_scope


def commit_db_item(db_item, add=False):
    with session_scope() as session:
        if add:
            session.add(db_item)
        else:
            session.merge(db_item)
        session.commit()


def create_or_update_db_item(db_item, new_item):
    """
    Updates an existing or creates a new database item.
    """
    with session_scope() as session:
        # if database item exists
        if db_item is not None:
            # returning if database item is unchanged 
            if db_item == new_item:
                return
            # updating database item otherwise
            else:
                db_item.update(new_item)
                session.merge(db_item)
        # creating database item otherwise
        else:
            session.add(new_item)
        session.commit()
