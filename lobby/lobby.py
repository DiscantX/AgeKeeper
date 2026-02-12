import argparse
import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterable, Optional, Callable

import aiohttp


WS_URL = "wss://data.aoe2lobby.com/ws/"
global last_match_ids
last_match_ids = []

## ---------------------------- Class declarations ---------------------------- ##
@dataclass(frozen=True)
class Subscription:
    type: str
    context: str
    ids: Optional[Iterable[str]] = None

    def to_message(self) -> str:
        payload = {"action": "subscribe", "type": self.type, "context": self.context}
        if self.ids:
            payload["ids"] = [str(item) for item in self.ids]
        json_string = json.dumps(payload, separators=(",", ":"))
        return json_string

## ---------------------------- Helper functions ---------------------------- ##
def load_game_data():
    with open('datasets/100.json', 'r') as f:
        data = json.load(f)
    return data

data = load_game_data()

def print_lobby_events(
    # subscriptions: Iterable[Subscription],
    event: Any,
) -> None:
    new_match_ids =get_new_match_ids(event)
    print_short_match_info(event, new_match_ids)

def get_match_by_id(event, match_id: str) -> Optional[dict]:
    if match_id is None:
        return None
    response_types = list(event.keys())
    response_type = response_types[0]
    event_data = event[response_type]
    return event_data.get(match_id)

def search_matches_for_player(player_name: str, matches) -> list[str]:
    # player_names = [get_player_slot(player_name, match) for match in matches]
    # print(player_names)
    matching_matches = next((match for match in matches if get_player_slot(player_name, match) is not None), None)
    return matching_matches
    
    # response_types = list(event.keys())
    # response_type = response_types[0]
    # event_data = event[response_type]

    # matching_match_ids = []
    # if match_ids is None:
    #     matches = event_data.items()
    # else:
    #     matches = [(match_id, event_data.get(match_id)) for match_id in match_ids if event_data.get(match_id) is not None]
    # for match_id, match_info in matches:
    #     slots = match_info.get("slots", {})
    #     for slot in slots.values():
    #         if slot.get("name") == player_name:
    #             matching_match_ids.append(match_id)
    #             break
    # return matching_match_ids
    
    matching_matches = []
    

def get_player_slot(player_name: str, match):
    lobby_slots = match.get("slots", {})
    player_slot = [lobby_slots[slot] for slot in lobby_slots.keys() if lobby_slots[slot].get("name") == player_name]
    if len(player_slot) > 0:
        return player_slot[0]
    return None

def get_response_type(event):
    response_types = list(event.keys())
    response_type = response_types[0]
    return response_type

def get_short_response_type(event):
    response_type = get_response_type(event)
    short_response_type = response_type.split("_")[0].capitalize() 
    return short_response_type   

def get_civ_name(civ_id: int) -> str:
    civilizations = data.get("civilizations", {})
    civ = civilizations.get(str(civ_id))
    return civ.get("name", "Unknown") if civ else "Random"

def print_short_match_info(event, match_ids: list[str]) -> None:
    response_type = get_response_type(event)
    short_response_type = get_short_response_type(event)
    event_data = event[response_type]
    for match_id in match_ids:
        match_info = event_data.get(match_id)
        if match_info:
            slots = match_info.get("slots", "Unknown")
            players = [player["name"] for player in slots.values() if player.get("name")]
            map = match_info.get("map_name", "Unknown")
            print(f"{short_response_type} (ID: {match_id}) | Map: {map}\t| Players: {', '.join(players)}")

def get_new_match_ids(event):
    new_match_ids = []
    response_types = list(event.keys())
    response_type = response_types[0]
    if "update" in response_type:
        event_data = event[response_type]
        current_match_ids = list(event_data.keys())
        if "spectate" in response_type:
            new_match_ids = current_match_ids
        if "lobby" in response_type:
            new_match_ids = _calc_new_match_ids(current_match_ids)
            global last_match_ids
            last_match_ids = current_match_ids

    return new_match_ids

def _calc_new_match_ids(current_match_ids: list[str]) -> list[str]:
    return [match_id for match_id in current_match_ids if match_id not in last_match_ids]

def _parse_ids(raw: Optional[str]) -> Optional[Iterable[str]]:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]

## ---------------------------- API Interaction ---------------------------- ##
def _decode_message(message: aiohttp.WSMessage) -> Optional[Any]:
    if message.type == aiohttp.WSMsgType.TEXT:
        text = message.data
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    if message.type == aiohttp.WSMsgType.BINARY:
        return message.data
    return None

async def _lobby_event_stream(
    subscriptions: Iterable[Subscription],
    url: str = WS_URL,
    heartbeat: float = 20.0,    # Seconds between heartbeat pings to keep the connection alive
    reconnect: bool = True,
    reconnect_min_delay: float = 1.0,
    reconnect_max_delay: float = 30.0,
) -> AsyncIterator[Any]:
    delay = reconnect_min_delay
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url, heartbeat=heartbeat) as ws:
                    for sub in subscriptions:
                        try:
                            await ws.send_str(sub.to_message())
                        except:
                            print("Error occurred while establishing subscription to server. Check that message is formatted correctly.")

                    delay = reconnect_min_delay
                    async for message in ws:
                        payload = _decode_message(message)
                        if payload is not None:
                            yield payload
        except asyncio.CancelledError:
            raise
        except Exception:
            if not reconnect:
                raise
        if not reconnect:
            break
        await asyncio.sleep(delay)
        delay = min(delay * 2, reconnect_max_delay)

def lobby_matches_subscription() -> Subscription:
    return Subscription(type="matches", context="lobby")

def spectate_matches_subscription() -> Subscription:
    return Subscription(type="matches", context="spectate")

def lobby_players_subscription(player_ids: Iterable[str]) -> Subscription:
    return Subscription(type="players", context="lobby", ids=player_ids)

#Testing
def spectate_players_subscription(player_ids: Iterable[str]) -> Subscription:
    return Subscription(type="players", context="spectate", ids=player_ids)

def lobby_elotypes_subscription(elotype_ids: Iterable[str]) -> Subscription:
    return Subscription(type="elotypes", context="lobby", ids=elotype_ids)

def subscribe(subscription_names: list[str], player_ids: list[str] = None, elotype_ids: list[str] = None):
    if isinstance(subscription_names, argparse.Namespace):
        args = subscription_names
        subscriptions = []
        if args.players:
            ids = _parse_ids(args.players)
            if not ids:
                raise ValueError("--players requires at least one id")
            subscriptions.append(lobby_players_subscription(ids))

        if args.elotypes:
            ids = _parse_ids(args.elotypes)
            if not ids:
                raise ValueError("--elotypes requires at least one id")
            subscriptions.append(lobby_elotypes_subscription(ids))
        if args.lobby:
            subscriptions.append(lobby_matches_subscription())
        if args.spectate:
            subscriptions.append(spectate_matches_subscription())
        # Default to lobby matches if no specific subscription type is provided
        else:
            subscriptions.append(lobby_matches_subscription())

        return subscriptions

    subscriptions = []
    for name in subscription_names:
        if name == "lobby":
            subscriptions.append(lobby_matches_subscription())
        elif name == "spectate":
            subscriptions.append(spectate_matches_subscription())
        elif name == "players":
            if player_ids is None:
                raise ValueError("Player IDs must be provided for 'players' subscription")
            subscriptions.append(lobby_players_subscription(player_ids))
        elif name == "spectate_players":
            if player_ids is None:
                raise ValueError("Player IDs must be provided for 'spectate_players' subscription")
            subscriptions.append(spectate_players_subscription(player_ids))
        elif name == "elotypes":
            if elotype_ids is None:
                raise ValueError("Elo type IDs must be provided for 'elotypes' subscription")
            subscriptions.append(lobby_elotypes_subscription(elotype_ids))
        else:
            raise ValueError(f"Unknown subscription name: {name}")
    return subscriptions

async def receive_lobby_events(subscriptions: Iterable[Subscription], callback: Callable, **kwargs) -> None:
    async for event in _lobby_event_stream(subscriptions=subscriptions, **kwargs):
        callback(event, **kwargs)

async def connect_to_subscriptions_async(subscriptions: list, callback: Callable, **kwargs) -> None:
    await receive_lobby_events(
        subscriptions=subscriptions,
        callback=callback,
        **kwargs
    )

def connect_to_subscriptions_task(subscriptions: list, callback: Callable, **kwargs):
    return asyncio.create_task(
        connect_to_subscriptions_async(
            subscriptions=subscriptions,
            callback=callback,
            **kwargs
        )
    )

def connect_to_subscriptions(subscriptions: list, callback: Callable, **kwargs):
    print(f"Connecting to subscriptions {subscriptions}...")
    asyncio.run(
        receive_lobby_events(
            subscriptions=subscriptions,
            callback=callback,
            **kwargs
        )
    )
## ---------------------------- CLI/Arg parser ---------------------------- ##
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AOE2Lobby websocket listener.")
    parser.add_argument(
        "--lobby",
        action="store_true",
        help="Subscribe to lobby matches.",
    )
    parser.add_argument(
        "--spectate",
        action="store_true",
        help="Subscribe to spectate matches.",
    )
    parser.add_argument(
        "--players",
        type=str,
        default=None,
        help="Comma-separated player profile IDs to track in lobby.",
    )
    parser.add_argument(
        "--elotypes",
        type=str,
        default=None,
        help="Comma-separated elo type IDs to track in lobby.",
    )
    return parser

## ---------------------------- Main ---------------------------- ##
def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    subscriptions = subscribe(args)
    connect_to_subscriptions(subscriptions, print_lobby_events)

if __name__ == "__main__":
    main()
