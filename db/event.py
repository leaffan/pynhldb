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

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.game_id, self.in_game_event_cnt, self.type, self.period,
                self.time, self.road_on_ice, self.home_on_ice, self.stop_type,
                self.road_goalie, self.home_goalie, self.road_score,
                self.home_score, self.raw_data
                ) == (
                other.game_id, other.in_game_event_cnt, other.type,
                other.period, other.time, other.road_on_ice, other.home_on_ice,
                other.stop_type, other.road_goalie, other.home_goalie,
                other.road_score, other.home_score, other.raw_data
                ))

    def __ne__(self, other):
        return not self == other

