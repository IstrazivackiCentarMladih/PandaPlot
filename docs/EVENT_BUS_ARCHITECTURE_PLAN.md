# Event Bus Architecture Implementation Plan

## Overview
This document outlines the plan for implementing an event bus system to replace the current signal-based communication in the pandaplot application. The goal is to decouple components and make the main window unaware of direct communication between components, creating a more maintainable and scalable architecture.

## Implementation Guide for GitHub Copilot

This document provides complete implementation patterns and examples for GitHub Copilot to generate consistent, well-structured event bus code. Follow these patterns exactly for consistent implementation across the codebase.

### Quick Reference for Copilot
- **Event Bus Pattern**: Use hierarchical events (generic → specific)
- **Naming Convention**: `[Domain]Events.[ACTION]_[OBJECT]` (e.g., `DatasetEvents.DATASET_CHANGED`)
- **Mixin Pattern**: Use `EventPublisherMixin` and `EventSubscriberMixin` for components
- **Multi-level Publishing**: Always publish multiple event levels (specific → generic)
- **Smart Subscription**: Components choose appropriate granularity level

## Current State Analysis (Updated August 2025)

### Current Implementation Status

✅ **Already Implemented:**
1. **Basic EventBus**: Simple event bus with `subscribe()` and `emit()` methods
2. **App Integration**: EventBus integrated into `AppContext` and `AppState`
3. **Project Events**: Project-related events are actively used in components
4. **Partial Component Migration**: Some components (ProjectViewPanel, TabContainer) use events

❌ **Still Missing:**
1. **Event Type Classes**: No formal event type definitions
2. **Event Mixins**: No reusable mixins for publishers/subscribers
3. **Advanced Features**: No middleware, filtering, or replay systems
4. **Signal Migration**: Many components still use Qt signals

### Current Signal-Based Architecture Issues
1. **Tight Coupling**: Components directly emit signals to specific targets
2. **Main Window Awareness**: Main window acts as a signal hub, knowing about all components
3. **Hard to Scale**: Adding new components requires modifying multiple existing components
4. **Testing Complexity**: Difficult to test components in isolation
5. **Event Flow Complexity**: Signal chains are hard to follow and debug

### Current Signal Usage Examples
```python
# Dataset Tab → Main Window → Analysis Panel (❌ Still using signals)
self.analysis_applied.emit(new_column_name)  # Analysis panel
self.data_changed.emit()                     # Dataset tab
self.title_changed.emit(title)               # Tab container

# Project Events → Event Bus (✅ Already migrated)
self.app_state.event_bus.emit('project_loaded', {...})
self.app_context.event_bus.subscribe('project_loaded', self.on_project_loaded)
```

## Event Bus Architecture Design

### Core Event Bus System

#### 1. Enhanced Event Bus Implementation
**File**: `pandaplot/models/events/event_bus.py` (⚠️ **NEEDS ENHANCEMENT**)

**Current Basic Implementation**:
```python
from collections import defaultdict

class EventBus:
    """A simple event bus for managing events and subscribers."""
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event_name, callback):
        self._subscribers[event_name].append(callback)

    def emit(self, event_name, data=None):
        for callback in self._subscribers[event_name]:
            callback(data)
```

**Enhanced Implementation Template for Copilot** (Simplified):
```python
"""
Simplified Event Bus with essential features only.

Features:
- Pattern-based subscriptions (e.g., "dataset.*" matches all dataset events)
- Automatic hierarchical event emission using EventHierarchy mapping
- Thread-safe operations
- Simple subscription management
- Optional debug logging

No complex features like middleware, replay, or performance monitoring.
"""

import logging
import threading
from typing import Callable, Dict, List, Any, Optional
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

class EventBus:
    """
    Simplified event bus with automatic hierarchy and pattern matching.
    
    Features:
    - Pattern subscriptions (e.g., "dataset.*" matches all dataset events)
    - Automatic event hierarchy using EventHierarchy.get_hierarchy()
    - Thread-safe operations
    - Simple subscription management
    
    Usage:
        event_bus = EventBus()
        
        # Subscribe to patterns
        event_bus.subscribe("dataset.*", handler)
        
        # Emit with automatic hierarchy
        event_bus.emit("dataset.column_added", {"column": "new_col"})
        # Automatically emits hierarchy: dataset.column_added → dataset.structure_changed → dataset.changed
    """
    
    def __init__(self, debug_logging: bool = False):
        self._subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self._pattern_subscriptions: List[tuple] = []  # (pattern, handler) pairs
        self._lock = threading.RLock()
        self._debug_logging = debug_logging
    
    def subscribe(self, event_pattern: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Subscribe to an event pattern.
        
        Args:
            event_pattern: Event type or pattern (e.g., "dataset.changed" or "dataset.*")
            handler: Function to call when event matches
            
        Examples:
            # Subscribe to specific event
            event_bus.subscribe("dataset.changed", self.on_dataset_changed)
            
            # Subscribe to all dataset events
            event_bus.subscribe("dataset.*", self.on_any_dataset_event)
        """
        with self._lock:
            is_pattern = '*' in event_pattern
            
            if is_pattern:
                self._pattern_subscriptions.append((event_pattern, handler))
            else:
                self._subscriptions[event_pattern].append(handler)
            
            if self._debug_logging:
                logger.debug(f"Subscribed to {event_pattern}")
    
    def unsubscribe(self, event_pattern: str, handler: Callable) -> None:
        """Unsubscribe from an event pattern."""
        with self._lock:
            is_pattern = '*' in event_pattern
            
            if is_pattern:
                self._pattern_subscriptions = [
                    (pattern, h) for pattern, h in self._pattern_subscriptions
                    if not (pattern == event_pattern and h == handler)
                ]
            else:
                if event_pattern in self._subscriptions:
                    if handler in self._subscriptions[event_pattern]:
                        self._subscriptions[event_pattern].remove(handler)
    
    def emit(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """
        Emit an event with automatic hierarchy.
        
        Args:
            event_type: The specific event type to emit
            data: Optional data to include with the event
            
        This automatically emits parent events based on EventHierarchy mapping.
        """
        from pandaplot.models.events.event_types import EventHierarchy
        
        event_data = data or {}
        event_data['timestamp'] = self._get_timestamp()
        
        # Get hierarchy for this event type
        hierarchy = EventHierarchy.get_hierarchy(event_type)
        
        if self._debug_logging:
            logger.debug(f"Emitting event hierarchy: {hierarchy}")
        
        # Emit each level in the hierarchy
        for event_level in hierarchy:
            level_data = event_data.copy()
            level_data['event_type'] = event_level
            level_data['original_event'] = event_type
            
            self._emit_to_subscribers(event_level, level_data)
    
    def _emit_to_subscribers(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Emit event to all matching subscribers."""
        with self._lock:
            # Exact match subscribers
            for handler in self._subscriptions[event_type]:
                self._call_handler(handler, event_data)
            
            # Pattern match subscribers
            for pattern, handler in self._pattern_subscriptions:
                if self._matches_pattern(event_type, pattern):
                    self._call_handler(handler, event_data)
    
    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches a pattern."""
        # Simple pattern matching - convert * to .*
        regex_pattern = pattern.replace('.', r'\.')
        regex_pattern = regex_pattern.replace('*', '.*')
        regex_pattern = f'^{regex_pattern}$'
        
        return bool(re.match(regex_pattern, event_type))
    
    def _call_handler(self, handler: Callable, event_data: Dict[str, Any]) -> None:
        """Safely call an event handler."""
        try:
            handler(event_data)
        except Exception as e:
            logger.error(f"Error in event handler: {e}")
            if self._debug_logging:
                logger.exception("Handler exception details:")
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def get_subscribers_count(self, event_pattern: str = None) -> int:
        """Get number of subscribers (for debugging)."""
        if event_pattern:
            if '*' in event_pattern:
                return len([h for p, h in self._pattern_subscriptions if p == event_pattern])
            else:
                return len(self._subscriptions[event_pattern])
        else:
            return (sum(len(handlers) for handlers in self._subscriptions.values()) + 
                   len(self._pattern_subscriptions))
```
            component_id = component_id or f"component_{id(handler)}"
            
            subscription = EventSubscription(
                event_pattern=event_pattern,
                handler=handler,
                priority=priority,
                component_id=component_id,
                is_pattern=is_pattern
            )
            
            if is_pattern:
                self._pattern_subscriptions.append(subscription)
                # Sort by priority
                self._pattern_subscriptions.sort(key=lambda s: s.priority.value, reverse=True)
            else:
                self._subscriptions[event_pattern].append(subscription)
                # Sort by priority
                self._subscriptions[event_pattern].sort(key=lambda s: s.priority.value, reverse=True)
            
            if self._debug_logging:
                logger.debug(f"Subscribed {component_id} to {event_pattern}")
            
            return subscription
    
    def emit(self, event_type: str, data: Dict[str, Any] = None, 
             emit_hierarchy: bool = None) -> None:
        """
        Emit an event to all matching subscribers.
        
        Args:
            event_type: The type of event to emit
            data: Optional data to include with the event
            emit_hierarchy: Override hierarchy emission setting
            
        Example:
            # Emit specific event
            event_bus.emit("dataset.column.added", {
                "dataset_id": "data1",
                "column_name": "new_column"
            })
            
            # This will also emit:
            # - "dataset.column" event
            # - "dataset" event
            # If hierarchy is enabled
        """
        emit_hierarchy = emit_hierarchy if emit_hierarchy is not None else self._enable_hierarchy
        event_data = data or {}
        
        # Add metadata
        event_data['event_type'] = event_type
        event_data['timestamp'] = self._get_timestamp()
        
        # Store in history
        self._add_to_history(event_type, event_data)
        
        if self._debug_logging:
            logger.debug(f"Emitting event: {event_type} with data: {event_data}")
        
        # Emit the specific event
        self._emit_to_subscribers(event_type, event_data)
        
        # Emit hierarchy events if enabled
        if emit_hierarchy:
            self._emit_hierarchy_events(event_type, event_data)
    
    def _emit_hierarchy_events(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Emit parent events in the hierarchy."""
        parts = event_type.split('.')
        for i in range(len(parts) - 1, 0, -1):
            parent_event = '.'.join(parts[:i])
            parent_data = event_data.copy()
            parent_data['child_event_type'] = event_type
            parent_data['event_type'] = parent_event
            
            if self._debug_logging:
                logger.debug(f"Emitting hierarchy event: {parent_event}")
            
            self._emit_to_subscribers(parent_event, parent_data)
```
        """Publish an event to all subscribers."""
        
    def add_middleware(self, middleware: Callable[[Event], Event]) -> None:
        """Add middleware for event processing."""
```

#### 2. Event Types Definition
**File**: `pandaplot/models/events/event_types.py` (❌ **NOT IMPLEMENTED**)

**Design Philosophy**: Hierarchical event types that allow components to subscribe at their appropriate level of granularity. Components can choose between generic events (for broad awareness) or specific events (for detailed handling).

**Implementation Template for Copilot**:
```python
"""
Event type definitions for the pandaplot application.
This module defines hierarchical event types following the pattern:
- Generic events for broad component awareness
- Specific events for detailed component handling

Usage patterns:
- Generic subscription: subscribe_to_event(DatasetEvents.DATASET_CHANGED, handler)
- Specific subscription: subscribe_to_event(DatasetOperationEvents.DATASET_COLUMN_ADDED, handler)
- Multi-level publishing: publish both specific and generic events
"""

class DatasetEvents:
    """Dataset-related events (generic dataset operations).
    
    Use these events when components need broad awareness of dataset changes
    without caring about specific operations.
    """
    # High-level dataset events
    DATASET_CHANGED = "dataset.changed"  # 🆕 Generic dataset change - use for broad awareness
    DATASET_STRUCTURE_CHANGED = "dataset.structure_changed"  # 🆕 Structure change - columns/rows modified
    DATASET_DATA_CHANGED = "dataset.data_changed"  # Data content change - cell values modified
    DATASET_SELECTED = "dataset.selected"  # Dataset selection change in UI
    
    # Lifecycle events
    DATASET_CREATED = "dataset.created"
    DATASET_UPDATED = "dataset.updated"
    DATASET_DELETED = "dataset.deleted"

class DatasetOperationEvents:
    """Specific dataset operation events.
    
    Use these events when components need detailed information about 
    specific dataset operations for precise handling.
    """
    # Column operations
    DATASET_COLUMN_ADDED = "dataset.column_added"
    DATASET_COLUMN_REMOVED = "dataset.column_removed"
    DATASET_COLUMN_RENAMED = "dataset.column_renamed"  # 🆕
    DATASET_COLUMN_REORDERED = "dataset.column_reordered"  # 🆕
    
    # Row operations
    DATASET_ROW_ADDED = "dataset.row_added"
    DATASET_ROW_REMOVED = "dataset.row_removed"
    DATASET_ROW_UPDATED = "dataset.row_updated"  # 🆕
    
    # Bulk operations
    DATASET_BULK_UPDATE = "dataset.bulk_update"  # 🆕
    DATASET_IMPORTED = "dataset.imported"
    DATASET_EXPORTED = "dataset.exported"  # 🆕

class AnalysisEvents:
    """Analysis-related events.
    
    Events for mathematical operations and analysis results.
    """
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"
    ANALYSIS_COLUMN_ADDED = "analysis.column_added"
    ANALYSIS_CONFIG_CHANGED = "analysis.config_changed"

class ChartEvents:
    """Chart-related events.
    
    Events for chart creation, updates, and interactions.
    """
    CHART_CREATED = "chart.created"
    CHART_UPDATED = "chart.updated"
    CHART_DELETED = "chart.deleted"
    CHART_STYLE_CHANGED = "chart.style_changed"
    CHART_DATA_UPDATED = "chart.data_updated"
    CHART_SELECTED = "chart.selected"

class UIEvents:
    """UI-related events.
    
    Events for user interface state changes and interactions.
    """
    TAB_CHANGED = "ui.tab_changed"
    TAB_CREATED = "ui.tab_created"
    TAB_CLOSED = "ui.tab_closed"
    TAB_TITLE_CHANGED = "ui.tab_title_changed"  # Added missing event
    PANEL_VISIBILITY_CHANGED = "ui.panel_visibility_changed"
    SIDEBAR_PANEL_SELECTED = "ui.sidebar_panel_selected"

class ProjectEvents:
    """Project-related events (✅ **PARTIALLY IMPLEMENTED**).
    
    Generic project events that are item-type agnostic.
    Use these when components need broad project awareness.
    """
    # High-level project events
    PROJECT_CREATED = "project.created"
    PROJECT_LOADED = "project.loaded"  # ✅ Used in current code
    PROJECT_SAVED = "project.saved"
    PROJECT_CLOSED = "project.closed"  # ✅ Used in current code
    PROJECT_SAVING = "project.saving"  # ✅ Currently used
    FIRST_PROJECT_LOADED = "first_project_loaded"  # ✅ Currently used
    
    # Generic project structure events (item-type agnostic)
    PROJECT_CHANGED = "project.changed"  # 🆕 Generic change event - use for broad awareness
    PROJECT_ITEM_ADDED = "project.item_added"  # Generic item added - use when type doesn't matter
    PROJECT_ITEM_REMOVED = "project.item_removed"  # Generic item removed
    PROJECT_ITEM_RENAMED = "project.item_renamed"  # Generic item renamed
    PROJECT_ITEM_MOVED = "project.item_moved"  # Generic item moved
    PROJECT_STRUCTURE_CHANGED = "project.structure_changed"  # 🆕 Structure change - folders/items reorganized

class FolderEvents:
    """Folder-specific events (✅ Currently used).
    
    Use these events when components need specific folder operation details.
    """
    FOLDER_CREATED = "folder.created"
    FOLDER_RENAMED = "folder.renamed"
    FOLDER_DELETED = "folder.deleted"
    FOLDER_MOVED = "folder.moved"

class NoteEvents:
    """Note-specific events (✅ Currently used).
    
    Use these events when components need specific note operation details.
    """
    NOTE_CREATED = "note.created"
    NOTE_RENAMED = "note.renamed"
    NOTE_DELETED = "note.deleted"
    NOTE_MOVED = "note.moved"
    NOTE_CONTENT_CHANGED = "note.content_changed"  # 🆕 For note content updates

class DatasetItemEvents:
    """Dataset item-specific events (✅ Currently used).
    
    Use these events when components need specific dataset item operation details.
    These are different from DatasetEvents - these are for dataset items in project tree,
    while DatasetEvents are for dataset data operations.
    """
    DATASET_ITEM_CREATED = "dataset_item.created"
    DATASET_ITEM_IMPORTED = "dataset_item.imported"
    DATASET_ITEM_REMOVED = "dataset_item.removed"
    DATASET_ITEM_RENAMED = "dataset_item.renamed"
    DATASET_ITEM_MOVED = "dataset_item.moved"
```

### Event Hierarchy Usage Examples for Copilot

**Generic Event Subscription Pattern** (for components that just need to know "something changed"):
```python
# Project view panel - just needs to refresh its display when anything changes
self.subscribe_to_event(ProjectEvents.PROJECT_CHANGED, self.refresh_project_display)

# Chart panel - needs to know if any dataset changed to refresh charts
self.subscribe_to_event(DatasetEvents.DATASET_CHANGED, self.refresh_charts)

# Auto-save - needs to know when project needs saving
self.subscribe_to_event(ProjectEvents.PROJECT_CHANGED, self.trigger_autosave)
```

**Specific Event Subscription Pattern** (for components that need detailed information):
```python
# Analysis panel - needs to know specific column operations to update UI choices
self.subscribe_to_event(DatasetOperationEvents.DATASET_COLUMN_ADDED, self.update_column_choices)
self.subscribe_to_event(DatasetOperationEvents.DATASET_COLUMN_REMOVED, self.remove_column_option)

# Folder management component - needs specific folder events for detailed handling
self.subscribe_to_event(FolderEvents.FOLDER_CREATED, self.handle_folder_creation)

# Statistics panel - needs specific operation counts
self.subscribe_to_event(DatasetOperationEvents.DATASET_ROW_ADDED, self.increment_row_count)
```

**Multi-Level Event Publishing Pattern** (always publish both generic and specific):
```python
# When a folder is created, publish multiple levels:
def create_folder(self, folder_data):
    # 1. Most specific - for components that handle folders specifically
    self.publish_event(FolderEvents.FOLDER_CREATED, {
        'folder_id': folder_data.id,
        'folder_name': folder_data.name,
        'parent_path': folder_data.parent_path
    })
    
    # 2. Medium specific - for components that track items generically
    self.publish_event(ProjectEvents.PROJECT_ITEM_ADDED, {
        'item_id': folder_data.id,
        'item_type': 'folder',
        'item_name': folder_data.name,
        'parent_path': folder_data.parent_path
    })
    
    # 3. Most generic - for broad awareness components
    self.publish_event(ProjectEvents.PROJECT_CHANGED, {
        'change_type': 'item_added',
        'item_type': 'folder'
    })

# When dataset data changes, publish multiple levels:
def on_dataset_data_changed(self, dataset_id, change_details):
    # 1. Most specific - for components that need operation details
    self.publish_event(DatasetOperationEvents.DATASET_ROW_ADDED, {
        'dataset_id': dataset_id,
        'row_index': change_details.row_index,
        'row_data': change_details.row_data
    })
    
    # 2. Medium specific - for components that track dataset structure
    self.publish_event(DatasetEvents.DATASET_STRUCTURE_CHANGED, {
        'dataset_id': dataset_id,
        'change_type': 'row_added',
        'new_shape': change_details.new_shape
    })
    
    # 3. Generic - for broad awareness
    self.publish_event(DatasetEvents.DATASET_CHANGED, {
        'dataset_id': dataset_id,
        'change_type': 'data_modified'
    })
    
    # 4. Most generic - for project-level awareness
    self.publish_event(ProjectEvents.PROJECT_CHANGED, {
        'change_type': 'dataset_modified',
        'dataset_id': dataset_id
    })
```

### Event Bus Integration Strategy

#### 3. Component Event Mixins
**File**: `pandaplot/models/events/mixins.py` (❌ **NOT IMPLEMENTED**)

**Implementation Template for Copilot**:
```python
"""
Event mixins for components that publish or subscribe to events.
These mixins provide standardized event handling patterns.

Usage patterns:
- EventPublisherMixin: for components that emit events
- EventSubscriberMixin: for components that listen to events
- Use both mixins for components that both publish and subscribe

Always call set_event_bus() in component __init__ to connect to the event bus.
"""

from typing import Callable, Dict, Any, List, Tuple
from pandaplot.models.events.event_bus import EventBus

class EventPublisherMixin:
    """Mixin for components that publish events.
    
    Provides standardized event publishing with automatic source tracking.
    Use this mixin for any component that needs to emit events.
    
    Example usage:
        class MyComponent(QWidget, EventPublisherMixin):
            def __init__(self, app_context):
                super().__init__()
                self.set_event_bus(app_context.event_bus)
                
            def on_something_changed(self):
                self.publish_event("something.changed", {"data": "value"})
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_bus: EventBus = None
    
    def set_event_bus(self, event_bus: EventBus) -> None:
        """Set the event bus for this component.
        
        Args:
            event_bus: The EventBus instance to use for publishing events
        """
        self._event_bus = event_bus
    
    def publish_event(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """Publish an event through the event bus with automatic hierarchy.
        
        Args:
            event_type: The most specific event type (e.g., "folder.created")
            data: Optional data to include with the event
            
        This automatically publishes the event hierarchy based on EventHierarchy mapping.
        For example, "folder.created" automatically publishes:
        - folder.created → project.item_added → project.changed
        
        Example:
            self.publish_event("folder.created", {
                'folder_id': folder.id,
                'folder_name': folder.name
            })
            # Automatically publishes all hierarchy levels
        """
        if self._event_bus:
            event_data = data or {}
            # Automatically add source information
            event_data['source_component'] = self.__class__.__name__
            event_data['source_id'] = id(self)
            
            # EventBus will handle hierarchy automatically using EventHierarchy mapping
            self._event_bus.emit(event_type, event_data)
    
    # Remove the complex publish_hierarchical_events method - no longer needed!

class EventSubscriberMixin:
    """Mixin for components that subscribe to events.
    
    Provides standardized event subscription with automatic cleanup.
    Use this mixin for any component that needs to listen to events.
    
    Example usage:
        class MyComponent(QWidget, EventSubscriberMixin):
            def __init__(self, app_context):
                super().__init__()
                self.set_event_bus(app_context.event_bus)
                self.setup_event_subscriptions()
                
            def setup_event_subscriptions(self):
                self.subscribe_to_event(DatasetEvents.DATASET_CHANGED, self.on_dataset_changed)
                
            def on_dataset_changed(self, event_data):
                # Handle the event
                pass
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_bus: EventBus = None
        self._subscriptions: List[Tuple[str, Callable]] = []
    
    def set_event_bus(self, event_bus: EventBus) -> None:
        """Set the event bus for this component.
        
        Args:
            event_bus: The EventBus instance to use for subscribing to events
        """
        self._event_bus = event_bus
    
    def subscribe_to_event(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to an event type.
        
        Args:
            event_type: The type of event to subscribe to (use constants from event_types.py)
            handler: Function to call when event is received (receives event data dict)
            
        Example:
            self.subscribe_to_event(DatasetEvents.DATASET_CHANGED, self.on_dataset_changed)
            
            def on_dataset_changed(self, event_data):
                dataset_id = event_data.get('dataset_id')
                # Handle the dataset change
        """
        if self._event_bus:
            self._event_bus.subscribe(event_type, handler)
            self._subscriptions.append((event_type, handler))
    
    def subscribe_to_multiple_events(self, event_subscriptions: List[Tuple[str, Callable]]) -> None:
        """Subscribe to multiple events at once.
        
        Args:
            event_subscriptions: List of (event_type, handler) tuples
            
        Example:
            self.subscribe_to_multiple_events([
                ("dataset.changed", self.on_dataset_changed),
                ("project.loaded", self.on_project_loaded),
                ("ui.tab_changed", self.on_tab_changed)
            ])
        """
        for event_type, handler in event_subscriptions:
            self.subscribe_to_event(event_type, handler)
    
    def subscribe_to_changes(self, scope: str, handler: Callable) -> None:
        """Subscribe to changes at the appropriate scope level.
        
        Args:
            scope: "dataset", "dataset_operations", "project", "project_items", "ui", "analysis"
            handler: Function to call when events match
            
        This automatically subscribes to the right granularity level:
        - "dataset": subscribes to "dataset.changed" (generic dataset changes)
        - "dataset_operations": subscribes to "dataset.*" (all dataset operations)
        - "project": subscribes to "project.changed" (generic project changes)
        - "project_items": subscribes to "project.item_*" (project item operations)
        """
        scope_patterns = {
            "dataset": "dataset.changed",  # Generic dataset changes only
            "dataset_operations": "dataset.*",  # All dataset operations
            "project": "project.changed",  # Generic project changes only
            "project_items": "project.item_*",  # Project item operations
            "ui": "ui.*",  # All UI events
            "analysis": "analysis.*",  # All analysis events
        }
        
        pattern = scope_patterns.get(scope, scope)
        self.subscribe_to_event(pattern, handler)
    
    def subscribe_to_specific_dataset(self, dataset_id: str, handler: Callable) -> None:
        """Subscribe to events for a specific dataset only.
        
        This replaces complex filtering with simple data checking.
        """
        def filtered_handler(event_data):
            if event_data.get('dataset_id') == dataset_id:
                handler(event_data)
        
        self.subscribe_to_event("dataset.*", filtered_handler)
    
    def unsubscribe_all(self) -> None:
        """Unsubscribe from all events.
        
        This should be called in component cleanup/destruction to prevent memory leaks.
        """
        if self._event_bus:
            for event_type, handler in self._subscriptions:
                # Note: This requires the EventBus to have an unsubscribe method
                # which needs to be implemented in the enhanced EventBus
                if hasattr(self._event_bus, 'unsubscribe'):
                    self._event_bus.unsubscribe(event_type, handler)
            self._subscriptions.clear()
    
    def __del__(self):
        """Cleanup subscriptions when component is destroyed."""
        self.unsubscribe_all()

class EventBusComponentMixin(EventPublisherMixin, EventSubscriberMixin):
    """Combined mixin for components that both publish and subscribe to events.
    
    Use this mixin for components that need both capabilities.
    This is the most common pattern for interactive components.
    
    Example usage:
        class AnalysisPanel(QWidget, EventBusComponentMixin):
            def __init__(self, app_context):
                super().__init__()
                self.set_event_bus(app_context.event_bus)
                self.setup_event_subscriptions()
                
            def setup_event_subscriptions(self):
                # Subscribe to events we care about
                self.subscribe_to_event(DatasetEvents.DATASET_CHANGED, self.on_dataset_changed)
                
            def apply_analysis(self):
                # Publish events when we do something
                self.publish_event(AnalysisEvents.ANALYSIS_COMPLETED, {
                    'analysis_type': 'correlation',
                    'dataset_id': self.current_dataset_id
                })
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
```

### Event Subscription Patterns for Copilot

**Basic Component Pattern** (subscribe to relevant events in __init__):
```python
class AnalysisPanel(QWidget, EventBusComponentMixin):
    def __init__(self, app_context: AppContext, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.set_event_bus(app_context.event_bus)
        
        # Setup UI first
        self.setup_ui()
        
        # Then setup event subscriptions
        self.setup_event_subscriptions()
    
    def setup_event_subscriptions(self):
        """Setup all event subscriptions for this component."""
        # Choose appropriate granularity for each subscription
        self.subscribe_to_multiple_events([
            # Generic events for broad awareness
            (DatasetEvents.DATASET_CHANGED, self.on_dataset_changed),
            (UIEvents.TAB_CHANGED, self.on_tab_changed),
            
            # Specific events for detailed handling
            (DatasetOperationEvents.DATASET_COLUMN_ADDED, self.on_column_added),
            (DatasetOperationEvents.DATASET_COLUMN_REMOVED, self.on_column_removed),
        ])
    
    def on_dataset_changed(self, event_data):
        """Handle generic dataset changes."""
        dataset_id = event_data.get('dataset_id')
        if dataset_id == self.current_dataset_id:
            self.refresh_ui_state()
    
    def on_column_added(self, event_data):
        """Handle specific column additions."""
        dataset_id = event_data.get('dataset_id')
        column_name = event_data.get('column_name')
        if dataset_id == self.current_dataset_id:
            self.add_column_to_choices(column_name)
```

**Event Publishing Pattern** (simplified - automatic hierarchy):
```python
def apply_analysis(self):
    """Apply analysis and publish event - hierarchy is automatic."""
    try:
        # Perform the analysis
        result = self.perform_analysis()
        
        # Publish just the most specific event - hierarchy is automatic!
        self.publish_event("analysis.completed", {
            'dataset_id': self.current_dataset_id,
            'analysis_type': self.analysis_type,
            'new_column_name': result.column_name,
            'analysis_config': self.get_analysis_config()
        })
        # EventHierarchy automatically publishes:
        # 1. analysis.completed
        # 2. dataset.column_added  
        # 3. dataset.changed
        
    except Exception as e:
        # Publish failure event
        self.publish_event("analysis.failed", {
            'dataset_id': self.current_dataset_id,
            'analysis_type': self.analysis_type,
            'error_message': str(e)
        })
```

**Subscription Pattern** (simplified - smart scopes):
```python
def setup_event_subscriptions(self):
    """Setup event subscriptions using smart scope patterns."""
    
    # Simple scope-based subscriptions (most common pattern)
    self.subscribe_to_changes("dataset", self.on_dataset_changed)  # Generic dataset changes
    self.subscribe_to_changes("ui", self.on_ui_changed)  # All UI events
    
    # For components that need detailed dataset operations
    self.subscribe_to_changes("dataset_operations", self.on_dataset_operation)  # All dataset.* events
    
    # For specific dataset tracking
    if hasattr(self, 'current_dataset_id'):
        self.subscribe_to_specific_dataset(self.current_dataset_id, self.on_my_dataset_changed)
    
    # Traditional specific event subscriptions still work
    self.subscribe_to_event("project.loaded", self.on_project_loaded)

def on_dataset_changed(self, event_data):
    """Handle generic dataset changes (gets all dataset.changed events)."""
    dataset_id = event_data.get('dataset_id')
    original_event = event_data.get('original_event')  # What actually happened
    
    # Simple broad refresh
    self.refresh_ui_state()

def on_dataset_operation(self, event_data):
    """Handle specific dataset operations (gets all dataset.* events)."""
    event_type = event_data.get('event_type')
    
    if event_type == 'dataset.column_added':
        self.add_column_to_choices(event_data.get('column_name'))
    elif event_type == 'dataset.column_removed':
        self.remove_column_from_choices(event_data.get('column_name'))
    # etc...
```

## Component Migration Plan

### Phase 1: Dataset Tab Migration

#### 4.1 Dataset Tab Event Integration
**File**: `pandaplot/gui/components/tabs/dataset_tab.py` (❌ **STILL USING SIGNALS**)

**Current Signal Usage**:
```python
title_changed = Signal(str)  # ❌ Still using Qt signals
data_changed = Signal()      # ❌ Still using Qt signals
```

**Recommended Event-Based Approach**:
```python
from pandaplot.models.events.mixins import EventPublisherMixin
from pandaplot.models.events.event_types import DatasetEvents, UIEvents

class DatasetTab(QWidget, EventPublisherMixin):
    def __init__(self, app_context: AppContext, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.set_event_bus(app_context.event_bus)  # Initialize event bus
        # ... existing initialization
    
    def on_data_changed(self):
        """Handle data changes and publish event."""
        self.publish_event(
            DatasetEvents.DATASET_DATA_CHANGED,
            {
                'dataset_id': self.dataset.id,
                'dataset_name': self.dataset.name,
                'shape': self.dataset.data.shape if self.dataset.data is not None else None
            }
        )
    
    def on_title_changed(self, new_title: str):
        """Handle title changes and publish event."""
        self.publish_event(
            UIEvents.TAB_TITLE_CHANGED,
            {
                'tab_id': id(self),
                'tab_type': 'dataset',
                'new_title': new_title,
                'dataset_id': self.dataset.id
            }
        )
```

### Phase 2: Analysis Panel Migration

#### 5.1 Analysis Panel Event Integration
**File**: `pandaplot/gui/components/sidebar/analysis/analysis_panel.py` (❌ **STILL USING SIGNALS**)

**Current Signal Usage**:
```python
analysis_applied = Signal(str)  # ❌ Still using Qt signals
```

**Recommended Event-Based Approach**:
```python
from pandaplot.models.events.mixins import EventPublisherMixin, EventSubscriberMixin
from pandaplot.models.events.event_types import AnalysisEvents, UIEvents, DatasetEvents, DatasetOperationEvents

class AnalysisPanel(QWidget, EventPublisherMixin, EventSubscriberMixin):
    def __init__(self, app_context: AppContext, parent=None):
        super().__init__(parent)
        self.set_event_bus(app_context.event_bus)  # Initialize event bus
        # ... existing initialization
        
        # Subscribe to relevant events (choose appropriate granularity)
        self.subscribe_to_event(UIEvents.TAB_CHANGED, self.on_tab_changed)
        
        # Generic dataset change (for broad awareness)
        self.subscribe_to_event(DatasetEvents.DATASET_CHANGED, self.on_dataset_changed)
        
        # Specific dataset operations (for detailed column handling)
        self.subscribe_to_event(DatasetOperationEvents.DATASET_COLUMN_ADDED, self.on_column_added)
        self.subscribe_to_event(DatasetOperationEvents.DATASET_COLUMN_REMOVED, self.on_column_removed)
    
    def on_analysis_applied(self, column_name: str):
        """Publish analysis completion event."""
        analysis_data = {
            'dataset_id': self.current_dataset_id,
            'new_column_name': column_name,
            'analysis_type': self.get_current_analysis_type(),
            'analysis_config': self.get_analysis_config()
        }
        
        # Publish specific analysis event
        self.publish_event(AnalysisEvents.ANALYSIS_COMPLETED, analysis_data)
        
        # Also publish generic dataset change (since analysis adds a column)
        self.publish_event(DatasetEvents.DATASET_CHANGED, {
            'dataset_id': self.current_dataset_id,
            'change_type': 'analysis_applied'
        })
    
    def on_tab_changed(self, event_data):
        """Handle tab change events."""
        if event_data.get('tab_type') == 'dataset':
            self.update_dataset_context(event_data.get('dataset_id'))
    
    def on_dataset_changed(self, event_data):
        """Handle generic dataset changes."""
        dataset_id = event_data.get('dataset_id')
        if dataset_id == self.current_dataset_id:
            self.refresh_ui_state()  # General refresh
    
    def on_column_added(self, event_data):
        """Handle specific column additions."""
        dataset_id = event_data.get('dataset_id')
        column_name = event_data.get('column_name')
        if dataset_id == self.current_dataset_id:
            self.add_column_to_choices(column_name)  # Specific action
    
    def on_column_removed(self, event_data):
        """Handle specific column removals."""
        dataset_id = event_data.get('dataset_id')
        column_name = event_data.get('column_name')
        if dataset_id == self.current_dataset_id:
            self.remove_column_from_choices(column_name)  # Specific action
```

### Phase 3: Main Window Decoupling

#### 6.1 Main Window Event Bus Integration
**File**: `pandaplot/gui/main_window.py`

**Current Approach** (Tightly Coupled):
```python
def setup_analysis_panel(self):
    self.analysis_panel.analysis_applied.connect(self.on_analysis_applied)

def on_analysis_applied(self, new_column_name: str):
    # Direct component interaction
    current_widget = self.tab_container.tab_widget.currentWidget()
    # ... complex signal chain logic
```

**New Event-Based Approach** (Decoupled):
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.event_bus = EventBus()
        self.setup_ui()
        self.setup_event_bus()
    
    def setup_event_bus(self):
        """Configure event bus for all components."""
        # Register components with event bus
        self.register_component_with_event_bus(self.analysis_panel)
        self.register_component_with_event_bus(self.transform_panel)
        self.register_component_with_event_bus(self.tab_container)
        
        # Main window only subscribes to high-level events it needs to handle
        self.event_bus.subscribe(ProjectEvents.PROJECT_LOADED, self.on_project_loaded)
        self.event_bus.subscribe(UIEvents.TAB_CLOSED, self.on_tab_closed)
    
    def register_component_with_event_bus(self, component):
        """Register a component with the event bus."""
        if hasattr(component, 'set_event_bus'):
            component.set_event_bus(self.event_bus)
```

### Phase 4: Tab Container Event Integration

#### 7.1 Tab Container Migration
**File**: `pandaplot/gui/components/tabs/tab_container.py` (🔄 **PARTIALLY MIGRATED**)

**Current State**: Already subscribes to project events, needs full event migration

**Current Event Usage** (✅ Already implemented):
```python
# In __init__:
if self.app_context and self.app_context.event_bus:
    self.app_context.event_bus.subscribe('project_loaded', self.on_project_loaded_event)
    self.app_context.event_bus.subscribe('project_closed', self.on_project_closed_event)
```

**Recommended Full Event-Based Approach**:
```python
from pandaplot.models.events.mixins import EventPublisherMixin, EventSubscriberMixin

class TabContainer(QWidget, EventPublisherMixin, EventSubscriberMixin):
    def __init__(self, app_context: AppContext, parent=None):
        super().__init__(parent)
        self.set_event_bus(app_context.event_bus)  # Initialize event bus
        # ... existing initialization
        
        # Subscribe to events (expand current subscriptions)
        self.subscribe_to_event(ProjectEvents.PROJECT_LOADED, self.on_project_loaded_event)
        self.subscribe_to_event(ProjectEvents.PROJECT_CLOSED, self.on_project_closed_event)
        self.subscribe_to_event(DatasetEvents.DATASET_DATA_CHANGED, self.on_dataset_updated)
        self.subscribe_to_event(AnalysisEvents.ANALYSIS_COMPLETED, self.on_analysis_completed)
    
    def on_tab_changed(self, index: int):
        """Handle tab changes and publish event."""
        current_widget = self.tab_widget.widget(index)
        tab_data = self.get_tab_data(current_widget)
        
        self.publish_event(
            UIEvents.TAB_CHANGED,
            {
                'tab_index': index,
                'tab_type': tab_data['type'],
                'tab_id': tab_data['id'],
                'dataset_id': tab_data.get('dataset_id'),
                'chart_id': tab_data.get('chart_id')
            }
        )
    
    def on_analysis_completed(self, event_data):
        """Handle analysis completion events."""
        dataset_id = event_data.get('dataset_id')
        # Find and refresh the relevant dataset tab
        for tab in self.get_dataset_tabs():
            if tab.get_dataset_id() == dataset_id:
                tab.load_dataset_data()  # Refresh without signal coupling
```

## Event Flow Examples

### 8.1 Analysis Workflow Event Flow (Hierarchical)
```
1. User applies analysis in Analysis Panel
   └── AnalysisPanel publishes multiple events:
       ├── AnalysisEvents.ANALYSIS_COMPLETED (specific)
       │   └── DatasetTab subscribes → updates analysis results display
       ├── DatasetOperationEvents.DATASET_COLUMN_ADDED (specific)
       │   └── TransformPanel subscribes → adds new column to choices
       └── DatasetEvents.DATASET_CHANGED (generic)
           ├── ChartPanel subscribes → refreshes charts using this dataset
           └── ProjectPanel subscribes → updates dataset info display

2. Components choose their subscription level based on needs
3. No main window involvement in component communication
```

### 8.2 Project Item Creation Event Flow (Hierarchical)
```
1. User creates a folder in Project Panel
   └── ProjectPanel publishes multiple events:
       ├── FolderEvents.FOLDER_CREATED (most specific)
       │   └── FolderSpecificComponent subscribes → handles folder-specific logic
       ├── ProjectEvents.PROJECT_ITEM_ADDED (item-type agnostic)
       │   └── ProjectStatistics subscribes → updates item count
       ├── ProjectEvents.PROJECT_STRUCTURE_CHANGED (structure-focused)
       │   └── ProjectTreeView subscribes → refreshes tree structure
       └── ProjectEvents.PROJECT_CHANGED (most generic)
           ├── ProjectTitle subscribes → updates "unsaved changes" indicator
           └── RecentProjects subscribes → updates last modified time

2. Each component gets exactly the level of detail it needs
3. Adding new components doesn't require changing existing ones
```

### 8.3 Dataset Update Event Flow (Multi-level)
```
1. Dataset data changes in Dataset Tab
   └── DatasetTab publishes hierarchical events:
       ├── DatasetOperationEvents.DATASET_ROW_ADDED (specific operation)
       │   └── DataStatistics subscribes → updates row count display
       ├── DatasetEvents.DATASET_STRUCTURE_CHANGED (structure-focused)
       │   └── DataValidation subscribes → re-validates data integrity
       ├── DatasetEvents.DATASET_CHANGED (generic dataset change)
       │   ├── AnalysisPanel subscribes → refreshes available operations
       │   └── ChartPanel subscribes → updates chart data
       └── ProjectEvents.PROJECT_CHANGED (project-level)
           └── AutoSave subscribes → triggers project auto-save

2. Fine-grained control over what each component cares about
3. Loose coupling - components only know what they need to know
```

## Simplified Event Bus Features

### 9.1 Essential Features Only
For this GUI application, we only need:

1. **Basic Event Bus** - Subscribe, emit, unsubscribe
2. **Pattern Subscriptions** - Subscribe to "dataset.*" to catch all dataset events
3. **Simple Hierarchical Events** - Automatic parent event emission
4. **Debug Logging** - Optional logging for development

**No need for complex features:**
- ❌ Event Replay System (too complex for GUI app)
- ❌ Event Filters (can be handled by smart subscription patterns)
- ❌ Event Middleware (adds unnecessary complexity)
- ❌ Performance Monitoring (simple GUI doesn't need this)

### 9.2 Simplified Multi-Level Event Publishing

**Problem**: Current approach requires manual tracking of multiple event levels.

**Solution**: Automatic hierarchy with smart event mapping.

**New Approach - Automatic Event Hierarchy**:
```python
from pandaplot.models.events.event_types import EventHierarchy

class EventPublisherMixin:
    """Simplified event publishing with automatic hierarchy."""
    
    def publish_event(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """Publish event with automatic hierarchy emission.
        
        Args:
            event_type: The most specific event type (e.g., "folder.created")
            data: Event data
            
        This automatically publishes parent events in the hierarchy:
        - "folder.created" → "project.item_added" → "project.changed"
        """
        if self._event_bus:
            event_data = data or {}
            event_data['source_component'] = self.__class__.__name__
            
            # Get hierarchy for this event type
            hierarchy = EventHierarchy.get_hierarchy(event_type)
            
            # Publish from specific to generic
            for event_level in hierarchy:
                level_data = event_data.copy()
                level_data['event_type'] = event_level
                level_data['original_event'] = event_type  # Track the original event
                
                self._event_bus.emit(event_level, level_data)

# Event hierarchy mapping - simple and maintainable
class EventHierarchy:
    """Defines automatic event hierarchy mappings."""
    
    # Simple mapping from specific events to their parent chain
    HIERARCHY_MAP = {
        # Folder events
        "folder.created": ["folder.created", "project.item_added", "project.changed"],
        "folder.renamed": ["folder.renamed", "project.item_renamed", "project.changed"],
        "folder.deleted": ["folder.deleted", "project.item_removed", "project.changed"],
        
        # Dataset item events
        "dataset_item.created": ["dataset_item.created", "project.item_added", "project.changed"],
        "dataset_item.imported": ["dataset_item.imported", "project.item_added", "project.changed"],
        
        # Dataset operation events
        "dataset.column_added": ["dataset.column_added", "dataset.structure_changed", "dataset.changed"],
        "dataset.row_added": ["dataset.row_added", "dataset.structure_changed", "dataset.changed"],
        "dataset.data_updated": ["dataset.data_updated", "dataset.changed"],
        
        # Analysis events
        "analysis.completed": ["analysis.completed", "dataset.column_added", "dataset.changed"],
        
        # UI events (no hierarchy needed)
        "ui.tab_changed": ["ui.tab_changed"],
        "ui.tab_closed": ["ui.tab_closed"],
    }
    
    @classmethod
    def get_hierarchy(cls, event_type: str) -> List[str]:
        """Get the event hierarchy for a given event type.
        
        Returns:
            List of event types from specific to generic
        """
        return cls.HIERARCHY_MAP.get(event_type, [event_type])
    
    @classmethod
    def add_mapping(cls, event_type: str, hierarchy: List[str]) -> None:
        """Add a new event hierarchy mapping (for extensions)."""
        cls.HIERARCHY_MAP[event_type] = hierarchy
```

## Migration Strategy (Updated for Current State)

### Phase 1: Foundation Enhancement (Week 1-2) - **PARTIALLY COMPLETE**
1. **✅ Basic Event Bus** - Already implemented
2. **❌ Event Types** - Create formal event type classes based on current usage
3. **❌ Event Mixins** - Create reusable mixins for components
4. **❌ Enhanced EventBus** - Add unsubscribe, middleware, and advanced features

### Phase 2: Component Migration (Week 3-5) - **IN PROGRESS**
1. **❌ Migrate Dataset Tab** 
   - Replace `title_changed` and `data_changed` signals with events
   - Test data change event flow
   - Ensure backward compatibility

2. **❌ Migrate Analysis Panel**
   - Replace `analysis_applied` signal with events
   - Subscribe to dataset events
   - Test analysis workflow

3. **❌ Migrate Transform Panel**
   - Similar migration to analysis panel
   - Ensure independent operation

### Phase 3: Tab Container and UI (Week 6-7) - **PARTIALLY COMPLETE**
1. **🔄 Tab Container** - Already subscribes to some events, needs full migration
   - Convert remaining tab change signals to events
   - Implement tab-specific event routing
   - Test tab switching workflow

2. **❌ Update Main Window**
   - Remove signal connections between components
   - Register components with event bus
   - Maintain only essential main window event subscriptions

### Phase 4: Advanced Features (Week 8-9) - **NOT STARTED**
### Phase 4: Testing and Validation (Week 8-9) - **SIMPLIFIED**
1. **Essential Testing Only**
   - Basic event flow testing
   - Component integration testing
   - Event hierarchy validation

2. **Simple Performance Validation**
   - Ensure events don't impact GUI responsiveness
   - Basic memory leak detection

### Phase 5: Chart Integration (Week 10) - **FUTURE**
1. **Prepare for Chart Enhancement**
   - Add chart events to EventHierarchy mapping
   - Design chart-specific events
   - Ensure compatibility with future chart features

---

## Implementation Checklist for GitHub Copilot - Simplified

### Step-by-Step Implementation Guide

**Phase 1: Simplified Event Bus** (Priority: High)
- [ ] Implement simplified EventBus with pattern matching
- [ ] Add automatic hierarchy emission using EventHierarchy mapping
- [ ] Add unsubscribe method for cleanup
- [ ] Create basic unit tests
- [ ] Remove unnecessary complexity (no priority, middleware, etc.)

**Phase 2: Event Hierarchy System** (Priority: High)
- [ ] Create EventHierarchy class with HIERARCHY_MAP
- [ ] Define simple event type constants (strings only)
- [ ] Implement get_hierarchy() method
- [ ] Add common event mappings (folder, dataset, analysis events)

**Phase 3: Simplified Component Mixins** (Priority: Medium)
- [ ] Create EventPublisherMixin with automatic hierarchy
- [ ] Create EventSubscriberMixin with smart scope patterns
- [ ] Create combined EventBusComponentMixin
- [ ] Add simple subscription cleanup

**Phase 4: Component Migration** (Priority: Medium)
- [ ] Migrate DatasetTab from Qt signals (use automatic hierarchy)
- [ ] Migrate AnalysisPanel from Qt signals (use smart scopes)
- [ ] Update remaining components
- [ ] Remove deprecated signal usage

**Phase 5: Simple Testing & Validation** (Priority: Low)
- [ ] Create basic event flow tests
- [ ] Add component integration tests
- [ ] Test event hierarchy mappings
- [ ] Verify no memory leaks

### Code Generation Patterns for Copilot

**When creating new components that use events:**
```python
class NewComponent(QWidget, EventBusComponentMixin):
    """Template for event-aware components."""
    
    def __init__(self, app_context: AppContext, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.set_event_bus(app_context.event_bus)
        
        # Setup UI first
        self.setup_ui()
        
        # Then setup events
        self.setup_event_subscriptions()
    
    def setup_event_subscriptions(self):
        """Setup all event subscriptions."""
        self.subscribe_to_multiple_events([
            # Add relevant event subscriptions
        ])
    
    def setup_ui(self):
        """Setup the user interface."""
        # UI setup code here
        pass
```

**When adding event publishing to existing components:**
```python
# Add mixin to class definition
class ExistingComponent(QWidget, EventPublisherMixin):
    
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        # Add event bus setup
        self.set_event_bus(app_context.event_bus)
    
    def some_action_method(self):
        """Method that performs action and publishes events."""
        # Perform the action
        result = self.do_something()
        
        # Publish single event - hierarchy is automatic!
        self.publish_event("component.action_completed", {
            'action_id': result.id,
            'details': result.details,
            'component_id': id(self),
        })
        # EventHierarchy automatically publishes:
        # component.action_completed → component.changed → project.changed
```

### Testing Patterns for Event-Driven Components

**Unit Test Template:**
```python
import pytest
from unittest.mock import Mock, patch
from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.events.event_types import DatasetEvents

class TestEventDrivenComponent:
    
    @pytest.fixture
    def event_bus(self):
        return EventBus()
    
    @pytest.fixture
    def component(self, event_bus):
        component = MyComponent()
        component.set_event_bus(event_bus)
        return component
    
    def test_component_publishes_event(self, component, event_bus):
        """Test that component publishes expected events."""
        handler = Mock()
        event_bus.subscribe("component.action", handler)
        
        # Trigger action
        component.perform_action()
        
        # Verify event was published
        handler.assert_called_once()
        event_data = handler.call_args[0][0]
        assert event_data['event_type'] == 'component.action'
    
    def test_component_handles_events(self, component, event_bus):
        """Test that component handles events correctly."""
        # Setup component state
        initial_state = component.get_state()
        
        # Emit event
        event_bus.emit("dataset.changed", {"dataset_id": "test"})
        
        # Verify component responded
        assert component.get_state() != initial_state
```

### Common Implementation Patterns

**Pattern 1: Data Change Broadcasting** (Simplified)
```python
def update_data(self, new_data):
    """Update data and broadcast change."""
    old_data = self.data
    self.data = new_data
    
    # Publish single specific event - hierarchy is automatic!
    self.publish_event("dataset.data_updated", {
        'dataset_id': self.dataset_id,
        'old_shape': old_data.shape if old_data is not None else None,
        'new_shape': new_data.shape,
        'row_count': len(new_data)
    })
    # EventHierarchy automatically publishes:
    # dataset.data_updated → dataset.changed → project.changed
```

**Pattern 2: UI State Synchronization** (Smart Scopes)
```python
def setup_event_subscriptions(self):
    """Subscribe to events that affect UI state."""
    # Use smart scope patterns
    self.subscribe_to_changes("dataset", self.on_dataset_changed)  # Generic dataset changes
    self.subscribe_to_changes("ui", self.on_ui_changed)  # All UI events
    self.subscribe_to_event("project.loaded", self.on_project_loaded)  # Specific events
        (ProjectEvents.PROJECT_LOADED, self.on_project_loaded),
    ])

def on_dataset_changed(self, event_data):
    """Handle dataset changes."""
    dataset_id = event_data.get('dataset_id')
    if dataset_id == self.current_dataset_id:
        self.refresh_display()
```

**Pattern 3: Cross-Component Communication**
```python
# Component A publishes
class ComponentA(QWidget, EventPublisherMixin):
    def perform_analysis(self):
        result = self.analyze()
        self.publish_event(AnalysisEvents.ANALYSIS_COMPLETED, {
            'analysis_id': result.id,
            'dataset_id': self.dataset_id,
            'result_data': result.data
        })

# Component B subscribes
class ComponentB(QWidget, EventSubscriberMixin):
    def setup_event_subscriptions(self):
        self.subscribe_to_event(
            AnalysisEvents.ANALYSIS_COMPLETED, 
            self.on_analysis_completed
        )
    
    def on_analysis_completed(self, event_data):
        analysis_id = event_data.get('analysis_id')
        self.display_analysis_result(analysis_id)
```

### Migration Guidelines

**From Qt Signals to Events:**
```python
# OLD: Qt Signal approach
class OldComponent(QWidget):
    data_changed = Signal(dict)  # ❌ Remove
    
    def update_data(self, data):
        self.data = data
        self.data_changed.emit({'data': data})  # ❌ Remove

# NEW: Event Bus approach
class NewComponent(QWidget, EventPublisherMixin):
    def __init__(self, app_context):
        super().__init__()
        self.set_event_bus(app_context.event_bus)  # ✅ Add
    
    def update_data(self, data):
        self.data = data
        # Publish single event with automatic hierarchy
        self.publish_event("dataset.data_updated", {  # ✅ Add
            'dataset_id': self.dataset_id,
            'data': data
        })
        # Automatically publishes: dataset.data_updated → dataset.changed
```

**Subscription Cleanup:**
```python
class ComponentWithCleanup(QWidget, EventSubscriberMixin):
    def closeEvent(self, event):
        """Ensure proper cleanup when component is closed."""
        self.unsubscribe_all()  # ✅ Always cleanup subscriptions
        super().closeEvent(event)
```

---

*End of Implementation Guide*

### Current Priority Actions:
1. **Create Event Type Classes** - Define all current event types formally
2. **Create Event Mixins** - Build reusable publisher/subscriber mixins
3. **Migrate Analysis Panel** - High-impact component with many signal connections
4. **Migrate Dataset Tab** - Core component that affects many others

## Benefits of Event Bus Architecture

### 1. Decoupling Benefits
- **Independent Components**: Components don't need to know about each other
- **Easy Testing**: Components can be tested in isolation with mock events
- **Scalability**: New components can be added without modifying existing ones
- **Maintainability**: Changes to one component don't affect others

### 2. Main Window Simplification
- **Reduced Complexity**: Main window no longer acts as signal hub
- **Single Responsibility**: Main window focuses on layout and high-level coordination
- **Cleaner Code**: Elimination of complex signal connection chains

### 3. Enhanced Debugging
- **Event Logging**: All inter-component communication is logged
- **Event Replay**: Ability to reproduce complex scenarios
- **Clear Event Flow**: Easy to trace event propagation

### 4. Future-Proofing
- **Plugin Architecture**: Easy to add new components and panels
- **Event Versioning**: Support for evolving event schemas
- **Distributed Components**: Potential for cross-process communication

## Testing Strategy

### 10.1 Unit Testing Events
```python
class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        bus.subscribe("test.event", handler)
        bus.publish(Event("test.event", "test_source"))
        
        assert len(received_events) == 1
        assert received_events[0].event_type == "test.event"
```

### 10.2 Integration Testing Components
```python
class TestDatasetTabEvents:
    def test_data_change_publishes_event(self):
        bus = EventBus()
        dataset_tab = DatasetTab(app_context, dataset)
        dataset_tab.set_event_bus(bus)
        
        received_events = []
        bus.subscribe(DatasetEvents.DATASET_DATA_CHANGED, received_events.append)
        
        dataset_tab.save_changes()  # Trigger data change
        
        assert len(received_events) == 1
        assert received_events[0].data['dataset_id'] == dataset.id
```

## Migration Compatibility

### 11.1 Backward Compatibility Strategy
- **Dual Mode Operation**: Support both signals and events during transition
- **Signal-to-Event Adapters**: Convert existing signals to events automatically
- **Gradual Migration**: Migrate components one by one without breaking others

### 11.2 Signal Adapter Pattern
```python
class SignalToEventAdapter:
    """Adapter to convert Qt signals to events."""
    def __init__(self, event_bus: EventBus, signal, event_type: str):
        self.event_bus = event_bus
        self.event_type = event_type
        signal.connect(self.on_signal_emitted)
    
    def on_signal_emitted(self, *args, **kwargs):
        """Convert signal emission to event publication."""
        self.event_bus.publish(Event(
            event_type=self.event_type,
            source="signal_adapter",
            data={'args': args, 'kwargs': kwargs}
        ))
```

This event bus implementation will significantly improve the architecture of the pandaplot application by eliminating tight coupling between components and creating a more maintainable, testable, and scalable system.

---

## Immediate Action Items (August 2025) - Simplified Approach

### Priority 1: Foundation Files to Create
1. **`pandaplot/models/events/event_types.py`** - Create EventHierarchy mapping class
   - Simple HIERARCHY_MAP dictionary mapping specific events to their parent chain
   - Clean event type constants (no complex classes needed)
   - EventHierarchy.get_hierarchy() method for automatic event chains

2. **Enhanced EventBus** - Simplify existing event bus (remove complexity)
   - Add unsubscribe method
   - Add pattern subscription support ("dataset.*")
   - Add automatic hierarchy emission using EventHierarchy
   - Remove unnecessary features (priority, middleware, recording)

3. **`pandaplot/models/events/mixins.py`** - Create simplified mixins
   - EventPublisherMixin with automatic hierarchy via publish_event()
   - EventSubscriberMixin with smart subscription patterns
   - No complex subscription management needed

### Priority 2: Smart Event Hierarchy Mapping
Define the simple HIERARCHY_MAP in event_types.py:
```python
HIERARCHY_MAP = {
    # Folder operations → item operations → project changes  
    "folder.created": ["folder.created", "project.item_added", "project.changed"],
    "folder.renamed": ["folder.renamed", "project.item_renamed", "project.changed"],
    
    # Dataset operations → dataset changes
    "dataset.column_added": ["dataset.column_added", "dataset.structure_changed", "dataset.changed"],
    "dataset.data_updated": ["dataset.data_updated", "dataset.changed"],
    
    # Analysis → dataset column → dataset change
    "analysis.completed": ["analysis.completed", "dataset.column_added", "dataset.changed"],
}
```

### Priority 3: Component Migration (Much Simpler Now)
1. **Analysis Panel** - Use simplified patterns:
   ```python
   # Publishing: Just publish the specific event, hierarchy is automatic
   self.publish_event("analysis.completed", analysis_data)
   
   # Subscribing: Use smart scope patterns
   self.subscribe_to_changes("dataset", self.on_dataset_changed)
   ```

2. **Dataset Tab** - Simplified event publishing:
   ```python
   # OLD: Complex multi-level publishing
   # NEW: Simple single event, automatic hierarchy
   self.publish_event("dataset.data_updated", {'dataset_id': self.dataset.id})
   ```

3. **Project Panel** - Use EventHierarchy mapping:
   ```python
   # Automatic hierarchy: folder.created → project.item_added → project.changed
   self.publish_event("folder.created", folder_data)
   ```

### Priority 4: Remove Complexity
1. **No Event Replay System** - Not needed for GUI application
2. **No Event Filters** - Use smart subscription patterns instead
3. **No Middleware** - Simple direct event handling
4. **No Priority System** - Events are fast enough for GUI
5. **No Complex Subscription Management** - Simple subscribe/unsubscribe is sufficient

### What We Removed vs. What We Kept

**❌ Removed (Over-engineered for GUI app):**
- Event Replay System
- Event Filters and Routing
- Event Middleware
- Priority-based delivery
- Performance monitoring
- Complex subscription objects
- Event history tracking

**✅ Kept (Essential for GUI app):**
- Pattern subscriptions ("dataset.*")
- Automatic event hierarchy (EventHierarchy mapping)
- Thread-safe operations
- Simple subscribe/unsubscribe
- Debug logging
- Smart subscription scopes

### Benefits of Simplified Approach:
1. **Much easier to implement** - Less code, fewer concepts
2. **Easier to understand** - Developers just publish specific events, hierarchy is automatic
3. **Less error-prone** - No manual hierarchy management
4. **Maintainable** - EventHierarchy mapping is easy to update
5. **Still powerful** - All the decoupling benefits without the complexity

### Files Still Using Signals (❌ Need Migration with Hierarchical Events):
- `pandaplot/gui/components/tabs/dataset_tab.py` - Migrate to publish dataset operation + generic events
- `pandaplot/gui/components/sidebar/analysis/analysis_panel.py` - Migrate to subscribe to appropriate event levels
- `pandaplot/gui/components/sidebar/transform/transform_panel.py` - Choose between specific column events vs generic dataset events
- `pandaplot/gui/components/tabs/chart_tab.py` - Subscribe to generic dataset events for broad awareness

### Event Granularity Design Benefits:
- **Loose Coupling**: Components only know what they need to know
- **Easy Extension**: New components can choose their appropriate subscription level
- **Performance**: Components can avoid unnecessary processing by subscribing to appropriate granularity
- **Maintainability**: Changes to specific events don't affect components using generic events

The hierarchical event bus architecture provides flexible subscription options while maintaining the decoupling benefits.
