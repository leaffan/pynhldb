#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base  # , session_scope
from db.specific_event import SpecificEvent
from db.event import Event
from db.player import Player


class Hit(Base, SpecificEvent):
    __tablename__ = 'hits'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone",
        "hit_taken_team_id", "hit_taken_player_id",
    ]

    def __init__(self, event_id, data_dict):
        self.hit_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    # @classmethod
    # def find_by_event_id(self, event_id):
    #     with session_scope() as session:
    #         try:
    #             hit = session.query(Hit).filter(
    #                 Hit.event_id == event_id
    #             ).one()
    #         except:
    #             hit = None
    #         return hit

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.event_id, self.team_id, self.player_id, self.zone,
                self.hit_taken_team_id, self.hit_taken_player_id
                ) == (
                other.event_id, other.team_id, other.player_id, other.zone,
                other.hit_taken_team_id, other.hit_taken_player_id
                ))

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        hit_plr = Player.find_by_id(self.player_id)
        taken_plr = Player.find_by_id(self.hit_taken_player_id)
        event = Event.find_by_id(self.event_id)
        return "Hit: %s on %s (%d/%s)" % (
            hit_plr.name, taken_plr.name, event.period, event.time)
