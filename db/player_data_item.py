#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import Base, session_scope
from .player import Player


class PlayerDataItem(Base):
    __tablename__ = 'player_data'
    __autoload__ = True

    STANDARD_ATTRS = [
        'height_imperial', 'height_metric',
        'weight_imperial', 'weight_metric',
        'hand', 'date_of_birth', 'place_of_birth',
        'image', 'country']

    def __init__(self, player_id, plr_data_dict):

        self.player_id = player_id

        for attr in self.STANDARD_ATTRS:
            if attr in plr_data_dict:
                if attr == 'place_of_birth':
                    if type(plr_data_dict['place_of_birth']) is str:
                        self.location = plr_data_dict['place_of_birth']
                    else:
                        self.place_of_birth = plr_data_dict[
                            'place_of_birth'].location_id
                else:
                    setattr(self, attr, plr_data_dict[attr])

    @classmethod
    def find_by_player_id(self, player_id):
        """
        Finds player data for a player in the database.
        """
        with session_scope() as session:
            try:
                plr_data_item = session.query(PlayerDataItem).filter(
                    PlayerDataItem.player_id == player_id
                ).one()
            except:
                plr_data_item = None
            return plr_data_item

    @classmethod
    def find_by_player_ids(self, player_ids):
        """
        Finds player data for multiple players in the database.
        """
        with session_scope() as session:
            try:
                plr_infos = session.query(PlayerDataItem).filter(
                    PlayerDataItem.player_id.in_(player_ids)
                ).all()
            except:
                plr_infos = None
            return plr_infos

    def update(self, other):
        for attr in [
            'player_id', 'height_metric', 'height_imperial', 'height_imperial',
            'weight_metric', 'weight_imperial', 'hand', 'date_of_birth',
            'country', 'location'
        ]:
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            self.player_id,
            "%.2f" % round(self.height_metric, 2),
            "%.2f" % round(self.height_imperial, 2),
            self.weight_metric, self.weight_imperial, self.hand,
            self.date_of_birth, self.country, self.location) == (
            other.player_id,
            "%.2f" % round(other.height_metric, 2),
            "%.2f" % round(other.height_imperial, 2),
            other.weight_metric, other.weight_imperial, other.hand,
            other.date_of_birth, other.country, other.location)

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        out = list()
        plr = Player.find_by_id(self.player_id)
        if plr.position == 'G':
            shoots_catches = "Catches:"
        else:
            shoots_catches = "Shoots:"
        # TODO: place of birth
        if self.place_of_birth:
            pass
            # loc = Location.find_by_id(self.place_of_birth)
            # if loc.state_province:
            #     loc = ", ".join((loc.real_name, loc.state_province, loc.country))
            # else:
            #     loc = ", ".join((loc.real_name, loc.country))
        else:
            loc = self.location

        if self.height_metric is None:
            self.height_metric = 0
        if self.weight_metric is None:
            self.weight_metric = 0

        out.append("%s" % plr.name)
        out.append("Height: %.2f m - Weight: %d kg - %s %s" % (
            self.height_metric, self.weight_metric,
            shoots_catches, self.hand))
        out.append(u"Date of Birth: %s - Place of Birth: %s" % (
            self.date_of_birth.strftime("%B %d, %Y"), loc))

        return "\n".join(out)
