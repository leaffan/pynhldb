#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import and_

from .common import Base, session_scope


class Event(Base):
    __tablename__ = 'events'
    __autoload__ = True

    HUMAN_READABLE = 'event'

    STANDARD_ATTRS = [
        "game_id", "in_game_event_cnt", "type", "period", "time",
        "road_on_ice", "home_on_ice", "road_score", "home_score", "x", "y",
        "stop_type", "road_goalie", "home_goalie", "raw_data", "num_situation"
    ]

    def __init__(self, event_id, event_data_dict):
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in event_data_dict:
                setattr(self, attr, event_data_dict[attr])
            else:
                setattr(self, attr, None)

    @classmethod
    def find_for_game(cls, game_id):
        with session_scope() as session:
            try:
                events = session.query(Event).filter(
                    Event.game_id == game_id
                ).all()
            except Exception:
                events = list()
            return events

    @classmethod
    def find(self, game_id, in_game_event_cnt):
        with session_scope() as session:
            try:
                event = session.query(Event).filter(
                    and_(
                        Event.game_id == game_id,
                        Event.in_game_event_cnt == in_game_event_cnt
                    )).one()
            except Exception as e:
                event = None
            return event

    @classmethod
    def find_by_id(self, event_id):
        with session_scope() as session:
            try:
                event = session.query(Event).filter(
                    Event.event_id == event_id
                ).one()
            except Exception as e:
                event = None
            return event

    @classmethod
    def find_by_time_type(self, game_id, event_period, event_time, event_type):
        with session_scope() as session:
            try:
                event = session.query(Event).filter(
                    and_(
                        Event.game_id == game_id,
                        Event.period == event_period,
                        Event.time == event_time,
                        Event.type == event_type
                    )).all()
            except Exception as e:
                event = None
            return event

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            # avoiding to overwrite existing coordinates in database
            # with null values
            if attr in ['x', 'y']:
                if hasattr(self, attr) and getattr(other, attr) is None:
                    continue
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        # TODO: check why num_situation has to be stripped of white spaces to
        # make this work
        return (
            (
                self.game_id, self.in_game_event_cnt, self.type, self.period,
                self.time, self.road_on_ice, self.home_on_ice, self.stop_type,
                self.road_goalie, self.home_goalie, self.road_score,
                self.home_score, self.raw_data,
                self.num_situation.strip(), self.x, self.y
                ) == (
                other.game_id, other.in_game_event_cnt, other.type,
                other.period, other.time, other.road_on_ice, other.home_on_ice,
                other.stop_type, other.road_goalie, other.home_goalie,
                other.road_score, other.home_score, other.raw_data,
                other.num_situation.strip(), other.x, other.y
                ))

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return "(%d/%02d:%02d)" % (
            self.period, self.time.seconds // 60, self.time.seconds % 60)
