#!/usr/bin/env python
# -*- coding: utf-8 -*-

from db.shot import Shot


def test_find_by_event_id():
    shot = Shot.find_by_event_id(20160207550053)
    assert shot.team_id == 15
    assert shot.player_id == 8471702
    assert shot.zone == "Off"
    assert shot.goalie_team_id == 6
    assert shot.goalie_id == 8471695
    assert shot.shot_type == "Wrist"
    assert shot.distance == 31
    assert not shot.scored
    assert not shot.penalty_shot
