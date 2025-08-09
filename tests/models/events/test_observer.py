import pytest

from pandaplot.models.events.observer import Event, Observer, Observable


class TestEvent:
    """Test suite for the Event class."""
    
    def test_init_with_type_only(self):
        """Test Event initialization with only event type."""
        event = Event("test_event")
        
        assert event.event_type == "test_event"
        assert event.data is None
    
    def test_init_with_type_and_data(self):
        """Test Event initialization with type and data."""
        test_data = {"key": "value", "number": 42}
        event = Event("test_event", test_data)
        
        assert event.event_type == "test_event"
        assert event.data == test_data
    
    def test_init_with_none_data(self):
        """Test Event initialization with explicit None data."""
        event = Event("test_event", None)
        
        assert event.event_type == "test_event"
        assert event.data is None
    
    def test_init_with_various_data_types(self):
        """Test Event initialization with different data types."""
        test_cases = [
            ("string_data", "hello world"),
            ("int_data", 123),
            ("list_data", [1, 2, 3]),
            ("dict_data", {"a": 1, "b": 2}),
            ("bool_data", True),
            ("float_data", 3.14),
        ]
        
        for event_type, data in test_cases:
            event = Event(event_type, data)
            assert event.event_type == event_type
            assert event.data == data
    
    def test_repr_without_data(self):
        """Test string representation of Event without data."""
        event = Event("test_event")
        expected = "Event(type=test_event, data=None)"
        
        assert repr(event) == expected
    
    def test_repr_with_data(self):
        """Test string representation of Event with data."""
        event = Event("test_event", {"key": "value"})
        expected = "Event(type=test_event, data={'key': 'value'})"
        
        assert repr(event) == expected
    
    def test_repr_with_complex_data(self):
        """Test string representation of Event with complex data."""
        complex_data = {
            "string": "hello",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"inner": "value"}
        }
        event = Event("complex_event", complex_data)
        
        # Just verify it contains the key elements
        repr_str = repr(event)
        assert "Event(type=complex_event" in repr_str
        assert "string" in repr_str
        assert "number" in repr_str


class MockObserver(Observer):
    """Mock observer for testing."""
    
    def __init__(self):
        self.received_events = []
    
    def update(self, event: Event):
        self.received_events.append(event)


class TestObserver:
    """Test suite for the Observer base class."""
    
    def test_observer_is_abstract(self):
        """Test that Observer raises NotImplementedError when update is not implemented."""
        observer = Observer()
        event = Event("test_event")
        
        with pytest.raises(NotImplementedError, match="Subclasses should implement this method"):
            observer.update(event)
    
    def test_mock_observer_implementation(self):
        """Test that our MockObserver works correctly."""
        observer = MockObserver()
        event1 = Event("event1", "data1")
        event2 = Event("event2", "data2")
        
        observer.update(event1)
        observer.update(event2)
        
        assert len(observer.received_events) == 2
        assert observer.received_events[0] == event1
        assert observer.received_events[1] == event2


class TestObservable:
    """Test suite for the Observable class."""
    
    def test_init(self):
        """Test Observable initialization."""
        observable = Observable()
        
        assert hasattr(observable, '_observers')
        assert isinstance(observable._observers, set)
        assert len(observable._observers) == 0
    
    def test_add_observer(self):
        """Test adding an observer."""
        observable = Observable()
        observer = MockObserver()
        
        observable.add_observer(observer)
        
        assert observer in observable._observers
        assert len(observable._observers) == 1
    
    def test_add_multiple_observers(self):
        """Test adding multiple observers."""
        observable = Observable()
        observer1 = MockObserver()
        observer2 = MockObserver()
        observer3 = MockObserver()
        
        observable.add_observer(observer1)
        observable.add_observer(observer2)
        observable.add_observer(observer3)
        
        assert len(observable._observers) == 3
        assert observer1 in observable._observers
        assert observer2 in observable._observers
        assert observer3 in observable._observers
    
    def test_add_duplicate_observer(self):
        """Test that adding the same observer twice doesn't create duplicates."""
        observable = Observable()
        observer = MockObserver()
        
        observable.add_observer(observer)
        observable.add_observer(observer)  # Add same observer again
        
        assert len(observable._observers) == 1
        assert observer in observable._observers
    
    def test_add_observer_callback(self):
        """Test adding a callback function as an observer."""
        observable = Observable()
        received_events = []
        
        def callback(event: Event):
            received_events.append(event)
        
        observable.add_observer_callback(callback)
        
        # Should have created one observer
        assert len(observable._observers) == 1
        
        # Test that the callback works
        event = Event("test_event", "test_data")
        observable.notify(event)
        
        assert len(received_events) == 1
        assert received_events[0] == event
    
    def test_add_multiple_observer_callbacks(self):
        """Test adding multiple callback functions."""
        observable = Observable()
        received_events1 = []
        received_events2 = []
        
        def callback1(event: Event):
            received_events1.append(event)
        
        def callback2(event: Event):
            received_events2.append(event)
        
        observable.add_observer_callback(callback1)
        observable.add_observer_callback(callback2)
        
        assert len(observable._observers) == 2
        
        # Test notification reaches both callbacks
        event = Event("test_event", "test_data")
        observable.notify(event)
        
        assert len(received_events1) == 1
        assert len(received_events2) == 1
        assert received_events1[0] == event
        assert received_events2[0] == event
    
    def test_remove_observer(self):
        """Test removing an observer."""
        observable = Observable()
        observer1 = MockObserver()
        observer2 = MockObserver()
        
        observable.add_observer(observer1)
        observable.add_observer(observer2)
        assert len(observable._observers) == 2
        
        observable.remove_observer(observer1)
        
        assert len(observable._observers) == 1
        assert observer1 not in observable._observers
        assert observer2 in observable._observers
    
    def test_remove_nonexistent_observer(self):
        """Test removing an observer that wasn't added."""
        observable = Observable()
        observer1 = MockObserver()
        observer2 = MockObserver()
        
        observable.add_observer(observer1)
        
        # Try to remove observer that wasn't added - should not raise error
        observable.remove_observer(observer2)
        
        assert len(observable._observers) == 1
        assert observer1 in observable._observers
    
    def test_remove_observer_twice(self):
        """Test removing the same observer twice."""
        observable = Observable()
        observer = MockObserver()
        
        observable.add_observer(observer)
        observable.remove_observer(observer)
        
        # Try to remove again - should not raise error
        observable.remove_observer(observer)
        
        assert len(observable._observers) == 0
    
    def test_notify_single_observer(self):
        """Test notifying a single observer."""
        observable = Observable()
        observer = MockObserver()
        observable.add_observer(observer)
        
        event = Event("test_event", "test_data")
        observable.notify(event)
        
        assert len(observer.received_events) == 1
        assert observer.received_events[0] == event
    
    def test_notify_multiple_observers(self):
        """Test notifying multiple observers."""
        observable = Observable()
        observer1 = MockObserver()
        observer2 = MockObserver()
        observer3 = MockObserver()
        
        observable.add_observer(observer1)
        observable.add_observer(observer2)
        observable.add_observer(observer3)
        
        event = Event("test_event", "test_data")
        observable.notify(event)
        
        # All observers should receive the event
        assert len(observer1.received_events) == 1
        assert len(observer2.received_events) == 1
        assert len(observer3.received_events) == 1
        
        assert observer1.received_events[0] == event
        assert observer2.received_events[0] == event
        assert observer3.received_events[0] == event
    
    def test_notify_no_observers(self):
        """Test notifying when there are no observers."""
        observable = Observable()
        event = Event("test_event", "test_data")
        
        # Should not raise any error
        observable.notify(event)
    
    def test_notify_multiple_events(self):
        """Test notifying multiple events to observers."""
        observable = Observable()
        observer = MockObserver()
        observable.add_observer(observer)
        
        event1 = Event("event1", "data1")
        event2 = Event("event2", "data2")
        event3 = Event("event3", "data3")
        
        observable.notify(event1)
        observable.notify(event2)
        observable.notify(event3)
        
        assert len(observer.received_events) == 3
        assert observer.received_events[0] == event1
        assert observer.received_events[1] == event2
        assert observer.received_events[2] == event3
    
    def test_clear_observers(self):
        """Test clearing all observers."""
        observable = Observable()
        observer1 = MockObserver()
        observer2 = MockObserver()
        observer3 = MockObserver()
        
        observable.add_observer(observer1)
        observable.add_observer(observer2)
        observable.add_observer(observer3)
        
        assert len(observable._observers) == 3
        
        observable.clear_observers()
        
        assert len(observable._observers) == 0
    
    def test_clear_observers_empty(self):
        """Test clearing observers when there are none."""
        observable = Observable()
        
        # Should not raise any error
        observable.clear_observers()
        
        assert len(observable._observers) == 0
    
    def test_observer_exception_handling(self):
        """Test that exceptions in observers don't affect other observers."""
        observable = Observable()
        
        class ExceptionObserver(Observer):
            def update(self, event: Event):
                raise ValueError("Test exception")
        
        good_observer = MockObserver()
        bad_observer = ExceptionObserver()
        
        observable.add_observer(good_observer)
        observable.add_observer(bad_observer)
        
        event = Event("test_event", "test_data")
        
        # The exception should propagate (by design)
        with pytest.raises(ValueError, match="Test exception"):
            observable.notify(event)
    
    def test_observer_lifecycle(self):
        """Test complete observer lifecycle: add, notify, remove, notify again."""
        observable = Observable()
        observer1 = MockObserver()
        observer2 = MockObserver()
        
        # Add observers
        observable.add_observer(observer1)
        observable.add_observer(observer2)
        
        # First notification
        event1 = Event("event1", "data1")
        observable.notify(event1)
        
        assert len(observer1.received_events) == 1
        assert len(observer2.received_events) == 1
        
        # Remove one observer
        observable.remove_observer(observer1)
        
        # Second notification
        event2 = Event("event2", "data2")
        observable.notify(event2)
        
        # Observer1 should not receive second event
        assert len(observer1.received_events) == 1
        assert len(observer2.received_events) == 2
        
        # Clear all observers
        observable.clear_observers()
        
        # Third notification
        event3 = Event("event3", "data3")
        observable.notify(event3)
        
        # No observer should receive third event
        assert len(observer1.received_events) == 1
        assert len(observer2.received_events) == 2
    
    def test_observer_callback_integration(self):
        """Test integration between regular observers and callback observers."""
        observable = Observable()
        regular_observer = MockObserver()
        callback_events = []
        
        def callback(event: Event):
            callback_events.append(event)
        
        observable.add_observer(regular_observer)
        observable.add_observer_callback(callback)
        
        event = Event("test_event", "test_data")
        observable.notify(event)
        
        # Both regular observer and callback should receive the event
        assert len(regular_observer.received_events) == 1
        assert len(callback_events) == 1
        assert regular_observer.received_events[0] == event
        assert callback_events[0] == event
    
    def test_observer_set_behavior(self):
        """Test that observers are stored in a set (no ordering guarantees)."""
        observable = Observable()
        
        # Test that _observers is indeed a set
        assert isinstance(observable._observers, set)
        
        # Test set-like behavior with custom observer classes
        class NamedObserver(Observer):
            def __init__(self, name):
                self.name = name
            
            def update(self, event: Event):
                pass
            
            def __eq__(self, other):
                return isinstance(other, NamedObserver) and self.name == other.name
            
            def __hash__(self):
                return hash(self.name)
        
        observer1 = NamedObserver("test")
        observer2 = NamedObserver("test")  # Same name, should be considered equal
        
        observable.add_observer(observer1)
        observable.add_observer(observer2)  # Should not add duplicate
        
        assert len(observable._observers) == 1
