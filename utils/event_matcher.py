#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)


def is_matching_event(play, event):
    """
    Checks whether specified play (retrieved from json data) and database event
    match.
    """
    if play['play_type'] == 'PENL':
        return is_matching_penalty_event(event, play)
    # elif event.type in ['HIT', 'BLOCK', 'FAC']:
    #     return is_matching_hit_block_faceoff_event(play, event)
    # elif event.type in ['GIVE', 'TAKE']:
    #     return is_matching_giveaway_takeaway_event(play, event)    
    # elif event.type in ['SHOT', 'GOAL']:
    #     return is_matching_shot_event(play, event)
    # elif event.type == 'MISS':
    #     return is_matching_miss_event(play, event)

    return False


def is_matching_penalty_event(penalty, play):
    """
    Checks whether the given play retrieved from json data matches with the
    specified (penalty) event.
    """
    print("\tid ", play['active'], penalty.player_id)
    print("\tpim ", play['pim'], penalty.pim)
    print("\tinfraction", play['infraction'], penalty.infraction.lower())

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
