"""In-memory match collection that stays in sync with lobby subscriptions."""

from lobby import lobby
from typing import Callable, Optional


class MatchBook:
    # Latest known spectate membership by player id so lobby removals can
    # suppress "left lobby" when the player transitioned into a game.
    _spectate_player_match_by_id: dict[str, str] = {}
    # Pending lobby-leave candidates keyed by player id. These are resolved by
    # player_status updates to avoid lobby/spectate stream ordering races.
    _pending_lobby_leaves: dict[str, dict] = {}

    def __init__(
        self,
        subscription_type: str,
        on_player_remove: Optional[Callable[[str, str, str, dict], None]] = None,
    ):
        self.subscription_type = subscription_type 
        self._matches = []
        self._subscriptions = lobby.subscribe([subscription_type])
        self._task = None
        self.on_player_remove = on_player_remove

    def __iter__(self):
        return iter(self._matches)

    def __len__(self):
        return len(self._matches)

    def __getitem__(self, index):
        return self._matches[index]

    def __str__(self):
        return str([match for match in self._matches])

    def start(self):
        if self._task is None:
            self._task = lobby.connect_to_subscriptions(
                self._subscriptions, self.update, create_task=True
            )
        return self._task

    def add(self, match):
        self._matches.append(match)

    def clear(self):
        self._matches.clear()

    def get_match_by_id(self, match_id):
        return next(
            (match for match in self._matches if str(match.get("matchid")) == str(match_id)),
            None,
        )

    def print_number_of_matches(self):
        print(f"Current number of {self.subscription_type} matches: {len(self)}")
    
    def add_matches(self, event):
        response_type = lobby.get_response_type(event)
        received_matches = [
            event.get(response_type, {}).get(match_id, {}) for match_id in event.get(response_type, [])
        ]
        old_matches = [
            match
            for match in self._matches
            if match.get("matchid") not in [m.get("matchid") for m in received_matches]
        ]
        self._matches = old_matches + received_matches

    def remove_matches(self, event):
        event_types = list(event.keys())
        if len(event_types) > 1:
            match_ids_to_remove = event.get(event_types[1])
            self._matches = [
                match
                for match in self._matches
                if str(match.get("matchid")) not in [str(id) for id in match_ids_to_remove]
            ]

    def _build_player_match_index(self):
        index = {}
        for match in self._matches:
            match_id = str(match.get("matchid"))
            slots = match.get("slots", {})
            if not isinstance(slots, dict):
                continue
            for slot in slots.values():
                if not isinstance(slot, dict):
                    continue
                player_id = slot.get("profileid")
                if player_id is None:
                    continue
                index[str(player_id)] = (match_id, match)
        return index

    def _player_remove_event_key(self):
        if self.subscription_type == "spectate":
            return "spectate_player_remove"
        if self.subscription_type == "lobby":
            return "lobby_player_remove"
        return None

    def _emit_player_remove_events(self, event, previous_player_index):
        event_key = self._player_remove_event_key()
        if not event_key:
            return
        removed_player_ids = event.get(event_key) or []
        if not isinstance(removed_player_ids, list):
            return

        for player_id in removed_player_ids:
            previous = previous_player_index.get(str(player_id))
            if not previous:
                continue
            match_id, match = previous
            if self.on_player_remove is not None:
                if self.subscription_type == "lobby":
                    self._queue_lobby_leave(str(player_id), str(match_id), match, self.on_player_remove)
                    continue
                self.on_player_remove(str(player_id), self.subscription_type, match_id, match)

    def _should_suppress_lobby_remove(self, event, player_id: str, match_id: str) -> bool:
        spectate_match_id = MatchBook._spectate_player_match_by_id.get(player_id)
        return spectate_match_id == match_id

    def _queue_lobby_leave(self, player_id: str, match_id: str, match: dict, callback: Callable):
        MatchBook._pending_lobby_leaves[player_id] = {
            "match_id": match_id,
            "match": match,
            "callback": callback,
        }

    @classmethod
    def resolve_pending_lobby_leave_from_player_status(cls, player_id: str, status: str, match_id) -> None:
        """
        Resolve one pending lobby leave with a player_status update.

        Rules:
        - status == 'spectate' and same match_id: suppress lobby leave.
        - Any other state transition: emit lobby leave.
        - status == 'lobby' with same match_id: still in lobby context, keep pending.
        """
        pending = cls._pending_lobby_leaves.get(str(player_id))
        if not pending:
            return

        pending_match_id = str(pending.get("match_id"))
        current_status = str(status or "").strip().lower()
        current_match_id = str(match_id) if match_id is not None else ""

        if current_status == "spectate" and current_match_id == pending_match_id:
            cls._pending_lobby_leaves.pop(str(player_id), None)
            return

        if current_status == "lobby" and current_match_id == pending_match_id:
            return

        cls._pending_lobby_leaves.pop(str(player_id), None)
        callback = pending.get("callback")
        if callback:
            callback(str(player_id), "lobby", pending_match_id, pending.get("match"))

    def _sync_shared_spectate_index(self):
        if self.subscription_type != "spectate":
            return
        MatchBook._spectate_player_match_by_id = {
            player_id: match_id for player_id, (match_id, _) in self._build_player_match_index().items()
        }

    def update(self, event):
        previous_player_index = self._build_player_match_index()
        self.add_matches(event)
        self.remove_matches(event)
        self._sync_shared_spectate_index()
        self._emit_player_remove_events(event, previous_player_index)
