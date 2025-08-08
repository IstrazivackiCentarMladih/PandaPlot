from collections import defaultdict
import re
from typing import Callable, Dict, Any
from .event_types import EventHierarchy


class EventBus:
    """Enhanced event bus with pattern matching and hierarchical event support.
    
    Features:
    - Pattern subscriptions (e.g., "dataset.*" to catch all dataset events)
    - Automatic event hierarchy emission using EventHierarchy mapping
    - Thread-safe operations for GUI use
    - Unsubscribe capability for cleanup
    """
    
    def __init__(self):
        self._subscribers = defaultdict(list)
        self._pattern_subscribers = defaultdict(list)

    def subscribe(self, event_pattern: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to events matching a pattern.
        
        Args:
            event_pattern: Event name or pattern (e.g., "dataset.changed" or "dataset.*")
            callback: Function to call when event matches
        """
        if '*' in event_pattern:
            # Convert glob pattern to regex
            regex_pattern = event_pattern.replace('.', r'\.').replace('*', '.*')
            self._pattern_subscribers[regex_pattern].append(callback)
        else:
            self._subscribers[event_pattern].append(callback)

    def unsubscribe(self, event_pattern: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a subscription.
        
        Args:
            event_pattern: The same pattern used in subscribe
            callback: The same callback function used in subscribe
        """
        if '*' in event_pattern:
            regex_pattern = event_pattern.replace('.', r'\.').replace('*', '.*')
            if callback in self._pattern_subscribers[regex_pattern]:
                self._pattern_subscribers[regex_pattern].remove(callback)
        else:
            if callback in self._subscribers[event_pattern]:
                self._subscribers[event_pattern].remove(callback)

    def emit(self, event_type: str, data: Dict[str, Any] | None = None) -> None:
        """Emit an event with automatic hierarchy support.
        
        Args:
            event_type: The most specific event type
            data: Event data dictionary
            
        This automatically emits parent events in the hierarchy based on EventHierarchy mapping.
        """
        if data is None:
            data = {}
        
        # Get hierarchy for this event type
        hierarchy = EventHierarchy.get_hierarchy(event_type)
        
        # Emit events from specific to generic
        for event_level in hierarchy:
            event_data = data.copy()
            event_data['event_type'] = event_level
            event_data['original_event'] = event_type
            
            # Emit to exact subscribers
            for callback in self._subscribers[event_level]:
                try:
                    callback(event_data)
                except Exception as e:
                    print(f"Error in event callback for {event_level}: {e}")
            
            # Emit to pattern subscribers
            for pattern, callbacks in self._pattern_subscribers.items():
                if re.match(pattern, event_level):
                    for callback in callbacks:
                        try:
                            callback(event_data)
                        except Exception as e:
                            print(f"Error in pattern callback for {event_level}: {e}")

    def clear_all_subscriptions(self) -> None:
        """Clear all subscriptions - useful for testing."""
        self._subscribers.clear()
        self._pattern_subscribers.clear()
