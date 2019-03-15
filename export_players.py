#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

from db.common import session_scope
from db.player import Player

if __name__ == '__main__':

    player_export = dict()

    with session_scope() as session:
        players = session.query(Player).order_by(Player.player_id).all()

        print("+ Exporting %d players from database" % len(players))

    for plr in players[:]:
        player_export[plr.player_id] = dict()
        player_export[plr.player_id]['first_name'] = plr.first_name
        player_export[plr.player_id]['last_name'] = plr.last_name
        player_export[plr.player_id]['position'] = plr.position
        if plr.alternate_first_names:
            player_export[plr.player_id][
                'alternate_first_names'] = plr.alternate_first_names
        if plr.alternate_last_names:
            player_export[plr.player_id][
                'alternate_last_names'] = plr.alternate_last_names
        if plr.alternate_positions:
            player_export[plr.player_id][
                'alternate_positions'] = plr.alternate_positions
        if plr.capfriendly_id:
            player_export[plr.player_id]['capfriendly_id'] = plr.capfriendly_id

    tgt_path = os.path.join('setup', 'nhl_players.json')

    open(tgt_path, 'w').write(json.dumps(player_export, indent=2))
