"""
BotBook Event Bus

Agents publish events.
Other agents subscribe.
"""

from typing import Dict, List, Callable

class EventBus:

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def publish(self, event_type: str, payload: dict):

        if event_type not in self.subscribers:
            return

        for callback in self.subscribers[event_type]:
            callback(payload)

    def subscribe(self, event_type: str, handler: Callable):

        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)


event_bus = EventBus()
