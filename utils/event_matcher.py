#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from db.event import Event
from db.shot import Shot
from db.shootout_attempt import ShootoutAttempt

logger = logging.getLogger(__name__)


# the *other* player for certain events, i.e. the faceoff loser, a player
# taking a hit or one having a shot blocked, is not registered under a
# consistently column name in the database
# that is why we have to map the according database columns to the
# corresponding event types
EVENT_PLAYER_ATTRIBUTE_NAMES = {
    'FAC': 'faceoff_lost_player_id',
    'HIT': 'hit_taken_player_id',
    'BLOCK': 'blocked_player_id'
}


def is_matching_event(play, specific_event):
    """
    Checks whether specified play (retrieved from json data) and database event
    match.
    """
    if play['play_type'] == 'PENL':
        return is_matching_penalty_event(specific_event, play)
    elif play['play_type'] in ['HIT', 'BLOCK', 'FAC']:
        return is_matching_hit_block_faceoff_event(specific_event, play)
    elif play['play_type'] in ['GIVE', 'TAKE']:
        return is_matching_giveaway_takeaway_event(specific_event, play)
    elif play['play_type'] in ['SHOT', 'GOAL']:
        return is_matching_shot_event(specific_event, play)
    elif play['play_type'] == 'MISS':
        return is_matching_miss_event(specific_event, play)

    return False


def is_matching_penalty_event(penalty, play):
    """
    Checks whether the given play retrieved from json data matches with the
    specified (penalty) event.
    """
    # print("\tid ", play['active'], penalty.player_id)
    # print("\tpim ", play['pim'], penalty.pim)
    # print("\tinfraction", play['infraction'], penalty.infraction.lower())

    # trying to match play and (team) penalty (i.e. not being given to a
    # certain player) using penalty minutes and sanctioned infraction
    if penalty.player_id is None:
        if (
            play['pim'], play['infraction']
        ) == (
            penalty.pim, penalty.infraction.lower()
        ):
            # TODO: logger.debug
            return True
    else:
        # trying to match play and penalty using participating players
        # (including the one drawing the penalty), penalty minutes and
        # sanctioned infraction
        if play['active'] is not None and play['passive'] is not None:
            if (
                play['active'], play['passive'],
                play['pim'], play['infraction']
            ) == (
                penalty.player_id, penalty.drawn_player_id,
                penalty.pim, penalty.infraction.lower()
            ):
                # TODO: logger.debug
                return True
        # trying to match play and penalty using participating player,
        # penalty minutes and sanctioned infraction
        elif play['active'] is not None:
            if (
                play['active'], play['pim'], play['infraction']
            ) == (
                penalty.player_id, penalty.pim, penalty.infraction.lower()
            ):
                # TODO: logger.debug
                return True

    return False


def is_matching_hit_block_faceoff_event(specific_event, play):
    """
    Tries to match given (hit, block or faceoff) event with specified play
    retrieved from json data.
    """
    # retrieving specific event
    event = Event.find_by_id(specific_event.event_id)
    # retrieving player id of hit, blocked, faceoff-losing player
    event_passive_player_id = getattr(
        specific_event, EVENT_PLAYER_ATTRIBUTE_NAMES[event.type])

    # trying to match using players involved in current event
    if (
            play['active'], play['passive']
    ) == (
            specific_event.player_id, event_passive_player_id
    ):
        # TODO: logger debug
        return True
    else:
        return False


def is_matching_giveaway_takeaway_event(specific_event, play):
    """
    Tries to match given (giveaway, takeaway) event with specified play
    retrieved from json data.
    """
    if (play['active']) == (specific_event.player_id):
        return True
    else:
        return False


def is_matching_shot_event(specific_event, play):
    """
    Tries to match given (regular/shootout shot) event with specified play
    retrieved from json data. This includes shots that turned into goals.
    """
    # retrieving base event
    event = Event.find_by_id(specific_event.event_id)
    # if it's a goal we have to retrieve the accompanying shot separately
    if event.type == 'GOAL':
        # it could be a shot in a shootout, too
        if play['period_type'] == 'SHOOTOUT':
            specific_event = ShootoutAttempt.find_by_event_id(event.event_id)
        else:
            specific_event = Shot.find_by_event_id(event.event_id)

    if (
        play['active'], play['shot_type']
    ) == (
        specific_event.player_id, specific_event.shot_type.lower()
    ):
        return True
    else:
        return False


def is_matching_miss_event(specific_event, play):
    """
    Tries to match given (regular/shootout shot) event with specified play
    retrieved from json data.
    """
    # retrieving base event
    event = Event.find_by_id(specific_event.event_id)

    if play['period_type'] == 'SHOOTOUT':
        specific_event = ShootoutAttempt.find_by_event_id(event.event_id)

    if specific_event.miss_type:
        if specific_event.miss_type in play['description'] and \
                specific_event.player_id == play['active']:
            return True
    else:
        if specific_event.player_id == play['active']:
            return True

    return False
