#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from sqlalchemy import and_

from sqlalchemy import and_

from .common import Base, session_scope


class Event(Base):
    __tablename__ = 'events'
    __autoload__ = True

    STANDARD_ATTRS = [
        "game_id", "in_game_event_cnt", "type", "period", "time",
        "road_on_ice", "home_on_ice", "road_score", "home_score", "x", "y",
        "stop_type", "road_goalie", "home_goalie", "raw_data"
    ]

    def __init__(self, event_id, event_data_dict):
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in event_data_dict:
                setattr(self, attr, event_data_dict[attr])

    @classmethod
    def find(self, game_id, in_game_event_cnt):
        with session_scope() as session:
            try:
                event = session.query(Event).filter(
                    and_(
                        Event.game_id == game_id,
                        Event.in_game_event_cnt == in_game_event_cnt
                    )).one()
            except:
                event = None
            return event
