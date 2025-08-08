from typing import Any, Callable


class Event:
    """Base class for events."""

    def __init__(self, event_type: str, data: Any = None):
        self.event_type = event_type
        self.data = data

    def __repr__(self):
        return f"Event(type={self.event_type}, data={self.data})"


class Observer:
    def update(self, event: Event):
        """Handle the event notification."""
        raise NotImplementedError("Subclasses should implement this method.")


class Observable:
    """Class to manage observers and notify them of events."""

    def __init__(self):
        self._observers: set[Observer] = set()

    def add_observer(self, observer: Observer):
        """Add an observer to the list if not already present."""
        if observer not in self._observers:
            self._observers.add(observer)
    
    def add_observer_callback(self, callback: Callable[[Event], None]):
        """Add a callback as an observer."""
        class CallbackObserver(Observer):
            def update(self, event: Event):
                callback(event)

        self.add_observer(CallbackObserver())

    def remove_observer(self, observer: Observer):
        """Remove an observer from the list if present."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: Event):
        """Notify all observers of an event."""
        for observer in self._observers:
            observer.update(event)

    def clear_observers(self):
        """Clear all observers."""
        self._observers.clear()
