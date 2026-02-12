from lobby import lobby


class MatchBook:
    def __init__(self, subscription_type: str):
        self.subscription_type = subscription_type 
        self._matches = []
        self._subscriptions = lobby.subscribe([subscription_type])
        self._task = None

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
            self._task = lobby.connect_to_subscriptions_task(self._subscriptions, self.update)
        return self._task

    def add(self, match):
        self._matches.append(match)

    def clear(self):
        self._matches.clear()

    def print_number_of_matches(self):
        print(f"Current number of {self.subscription_type} matches: {len(self)}")
    
    def add_matches(self, event):
        response_type = lobby.get_response_type(event)
        received_matches = [
            event.get(response_type, {}).get(match_id, {}) for match_id in event.get(response_type, [])
        ]
        removed_matches = [
            match
            for match in self._matches
            if match.get("matchid") not in [m.get("matchid") for m in received_matches]
        ]
        self._matches = removed_matches + received_matches

    def remove_matches(self, event):
        event_types = list(event.keys())
        if len(event_types) > 1:
            match_ids_to_remove = event.get(event_types[1])
            self._matches = [
                match
                for match in self._matches
                if str(match.get("matchid")) not in [str(id) for id in match_ids_to_remove]
            ]

    def update(self, event):
        self.add_matches(event)
        self.remove_matches(event)
