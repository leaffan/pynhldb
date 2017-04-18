#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base, session_scope
from db.event import Event
from db.player import Player


class Faceoff(Base):
    __tablename__ = 'faceoffs'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "faceoff_lost_team_id",
        "faceoff_lost_player_id", "faceoff_lost_zone"
    ]

    def __init__(self, event_id, data_dict):
        self.faceoff_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                setattr(self, attr, None)

    @classmethod
    def find_by_event_id(self, event_id):
        with session_scope() as session:
            try:
                faceoff = session.query(Faceoff).filter(
                    Faceoff.event_id == event_id
                ).one()
            except:
                faceoff = None
            return faceoff

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.event_id, self.team_id, self.player_id, self.zone,
                self.faceoff_lost_team_id, self.faceoff_lost_player_id,
                self.faceoff_lost_zone,
                ) == (
                other.event_id, other.team_id, other.player_id, other.zone,
                other.faceoff_lost_team_id, other.faceoff_lost_player_id,
                other.faceoff_lost_zone,
                ))

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        won_plr = Player.find_by_id(self.player_id)
        lost_plr = Player.find_by_id(self.faceoff_lost_player_id)
        event = Event.find_by_id(self.event_id)
        return "Faceoff: %s won vs. %s (%s) (%d/%s)" % (
            won_plr.name, lost_plr.name, self.zone, event.period, event.time)
