#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from .common import Base, session_scope
from db.player import Player
from db.event import Event


class Penalty(Base):
    __tablename__ = 'penalties'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "zone", "", "drawn_team_id",
        "drawn_player_id", "served_player_id", "infraction", "pim"
    ]

    def __init__(self, event_id, penalty_data_dict):
        self.penalty_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in penalty_data_dict:
                setattr(self, attr, penalty_data_dict[attr])
            else:
                setattr(self, attr, None)

    @classmethod
    def find_by_event_id(self, event_id):
        with session_scope() as session:
            try:
                penalty = session.query(Penalty).filter(
                    Penalty.event_id == event_id
                ).one()
            except:
                penalty = None
            return penalty

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.event_id, self.team_id, self.player_id, self.zone,
                self.drawn_team_id, self.drawn_player_id,
                self.served_player_id, self.infraction, self.pim
                ) == (
                other.event_id, other.team_id, other.player_id, other.zone,
                other.drawn_team_id, other.drawn_player_id,
                other.served_player_id, other.infraction, other.pim
                ))

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        player = Player.find_by_id(self.player_id)
        event = Event.find_by_id(self.event_id)
        if player:
            return "%s: %d minutes for %s (%d/%s)" % (
                player.name, self.pim, self.infraction,
                event.period, event.time)
        else:
            return "Bench penalty: %d minutes for %s (%d/%s)" % (
                self.pim, self.infraction, event.period, event.time)
