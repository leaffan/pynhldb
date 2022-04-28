#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from .common import session_scope

logger = logging.getLogger()


def delete_db_item(db_item):
    with session_scope() as session:
        session.delete(db_item)
        session.commit()


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


def create_or_update_db_item_alternate(db_item, new_item):
    """
    Creates or updates a database item.
    """
    cls_name = new_item.__class__.HUMAN_READABLE

    with session_scope() as session:
        if db_item is not None:
            if db_item != new_item:
                logger.debug("\t+ Updating %s item" % cls_name)
                db_item.update(new_item)
                return_item = session.merge(db_item)
            else:
                return_item = db_item
        else:
            logger.debug("\t+ Adding %s item" % cls_name)
            session.add(new_item)
            return_item = new_item

        session.commit()

    return return_item
