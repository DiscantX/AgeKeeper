def extract_player_status_update(event):
    """Extract (player_id, status, match_id) from a player_status event payload."""
    player_status = event.get("player_status", {})
    player_id = list(player_status.keys())[0] if player_status else None
    if player_id is None:
        print("No player status found in event.")
        return None

    player_state = player_status.get(player_id) or {}
    status = player_state.get("status")
    match_id = player_state.get("matchid")
    return player_id, status, match_id
