#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from db.common import Base, session_scope
from db.team import Team
from db.player import Player
from db.event import Event


class Goal(Base):
    __tablename__ = 'goals'
    __autoload__ = True

    STANDARD_ATTRS = [
        "team_id", "player_id", "goal_against_team_id", "shot_id",
        "assist_1", "assist_2", "in_game_cnt", "in_game_team_cnt",
        "go_ahead_goal", "tying_goal", "empty_net_goal"
    ]

    def __init__(self, event_id, data_dict):
        self.goal_id = uuid.uuid4().urn
        self.event_id = event_id
        for attr in self.STANDARD_ATTRS:
            if attr in data_dict:
                setattr(self, attr, data_dict[attr])
            else:
                if attr in ['go_ahead_goal', 'tying_goal', 'empty_net_goal']:
                    setattr(self, attr, False)
                else:
                    setattr(self, attr, None)

    @classmethod
    def find_by_event_id(self, event_id):
        with session_scope() as session:
            try:
                goal = session.query(Goal).filter(
                    Goal.event_id == event_id
                ).one()
            except:
                goal = None
            return goal

    def update(self, other):
        for attr in self.STANDARD_ATTRS:
            setattr(self, attr, getattr(other, attr))

    def __eq__(self, other):
        return (
            (
                self.event_id, self.team_id, self.player_id,
                self.goal_against_team_id, self.shot_id, self.assist_1,
                self.assist_2, self.in_game_cnt, self.in_game_team_cnt,
                self.go_ahead_goal, self.tying_goal, self.empty_net_goal
                ) == (
                other.event_id, other.team_id, other.player_id,
                other.goal_against_team_id, other.shot_id, other.assist_1,
                other.assist_2, other.in_game_cnt, other.in_game_team_cnt,
                other.go_ahead_goal, other.tying_goal, other.empty_net_goal
                ))

    def __ne__(self, other):
        return not self == other

    # TODO: re-do this mess
    def __str__(self):
        event = Event.find_by_id(self.event_id)
        team = Team.find_by_id(self.team_id)
        player = Player.find_by_id(self.player_id)

        team_and_scorer = "Goal: %s (%s)" % (player.name, team.name)

        assistants = list()

        if self.assist_1:
            assistants.append(Player.find_by_id(self.assist_1))
            if self.assist_2:
                assistants.append(Player.find_by_id(self.assist_2))
        if assistants:
            if len(assistants) == 2:
                assists = "(%s, %s)" % tuple([a.name for a in assistants])
            elif len(assistants) == 1:
                assists = "(%s)" % assistants[0].name
        else:
            assists = "(Unassisted)"

        return ' '.join((team_and_scorer, assists, str(event)))
