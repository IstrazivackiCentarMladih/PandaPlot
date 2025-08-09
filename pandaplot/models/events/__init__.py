"""
Event system for pandaplot application.

This module provides a simplified event bus architecture for decoupling components.
"""

from .event_bus import EventBus
from .event_types import (
    DatasetEvents,
    DatasetOperationEvents,
    AnalysisEvents,
    ChartEvents,
    UIEvents,
    ProjectEvents,
    FolderEvents,
    NoteEvents,
    DatasetItemEvents,
    EventHierarchy
)
from .mixins import EventPublisherMixin, EventSubscriberMixin, EventBusComponentMixin

__all__ = [
    'EventBus',
    'DatasetEvents',
    'DatasetOperationEvents', 
    'AnalysisEvents',
    'ChartEvents',
    'UIEvents',
    'ProjectEvents',
    'FolderEvents',
    'NoteEvents',
    'DatasetItemEvents',
    'EventHierarchy',
    'EventPublisherMixin',
    'EventSubscriberMixin',
    'EventBusComponentMixin'
]