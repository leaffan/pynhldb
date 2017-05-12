#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.common import Base
from db.common import session_scope


class SpecificEvent():

    @classmethod
    def find_by_event_id(self, event_id):
        # retrieving table name for specific event
        table_name = self.__tablename__

        # finding class associated with table name
        for c in Base._decl_class_registry.values():
            if hasattr(c, '__tablename__') and c.__tablename__ == table_name:
                break

        # retrieving specific event with the associated class type
        with session_scope() as session:
            try:
                specific_event = session.query(c).filter(
                    c.event_id == event_id
                ).one()
            except:
                specific_event = None
            return specific_event

    def update(self, other):
        # copying each standard attribute value from other object to this one
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        # comparing each standard attribute value (and event id) of this object
        # with other one's
        return (
            [self.event_id] +
            [getattr(self, attr) for attr in self.STANDARD_ATTRS]
        ) == (
            [other.event_id] +
            [getattr(other, attr) for attr in other.STANDARD_ATTRS]
        )

    def __ne__(self, other):
        return not self == other
