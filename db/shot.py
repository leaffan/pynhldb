#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base, session_scope
from db.player import Player
from db.event import Event

class Shot(Base):
    __tablename__ = 'shots'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "goalie_team_id", "goalie_id",
        "shot_type", "distance", "scored", "penalty_shot"
    ]

    def __init__(self, event_id, data_dict):
        self.shot_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                if attr in ['scored', 'penalty_shot']:
                    setattr(self, attr, False)
                else:
                    setattr(self, attr, None)

    @classmethod
    def find_by_event_id(self, event_id):
        with session_scope() as session:
            try:
                shot = session.query(Shot).filter(
                    Shot.event_id == event_id
                ).one()
            except:
                shot = None
            return shot

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.event_id, self.team_id, self.player_id, self.zone,
                self.goalie_team_id, self.goalie_id, self.shot_type,
                self.distance, self.scored, self.penalty_shot
                ) == (
                other.event_id, other.team_id, other.player_id, other.zone,
                other.goalie_team_id, other.goalie_id, other.shot_type,
                other.distance, other.scored, other.penalty_shot
                ))

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        player = Player.find_by_id(self.player_id)
        goalie = Player.find_by_id(self.goalie_id)
        event = Event.find_by_id(self.event_id)
        if goalie is not None:
            return "%s: shot on goal (%s, %d ft) vs. %s (%d/%s)" % (
                player.name, self.shot_type, self.distance,
                goalie.name, event.period, event.time)
        else:
            return "%s: shot on goal (%s, %d ft) (%d/%s)" % (
                player.name, self.shot_type, self.distance,
                event.period, event.time)
