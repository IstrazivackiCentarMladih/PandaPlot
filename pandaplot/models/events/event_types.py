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

from typing import List, Dict

class AppEvents:
    """Application-wide events."""
    APP_CLOSING = "app.closing"


class DatasetEvents:
    """Dataset-related events (generic dataset operations).
    
    Use these events when components need broad awareness of dataset changes
    without caring about specific operations.
    """
    # High-level dataset events
    DATASET_CHANGED = "dataset.changed"  # Generic dataset change - use for broad awareness
    DATASET_STRUCTURE_CHANGED = "dataset.structure_changed"  # Structure change - columns/rows modified
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
    DATASET_COLUMN_RENAMED = "dataset.column_renamed"
    DATASET_COLUMN_REORDERED = "dataset.column_reordered"
    
    # Row operations
    DATASET_ROW_ADDED = "dataset.row_added"
    DATASET_ROW_REMOVED = "dataset.row_removed"
    DATASET_ROW_UPDATED = "dataset.row_updated"
    
    # Bulk operations
    DATASET_BULK_UPDATE = "dataset.bulk_update"
    DATASET_IMPORTED = "dataset.imported"
    DATASET_EXPORTED = "dataset.exported"


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
    CHART_PREVIEW_REQUESTED = "chart.preview_requested"


class UIEvents:
    """UI-related events.
    
    Events for user interface state changes and interactions.
    """
    TAB_CHANGED = "ui.tab_changed"
    TAB_CREATED = "ui.tab_created"
    TAB_CLOSED = "ui.tab_closed"
    TAB_TITLE_CHANGED = "ui.tab_title_changed"
    PANEL_VISIBILITY_CHANGED = "ui.panel_visibility_changed"
    SIDEBAR_PANEL_SELECTED = "ui.sidebar_panel_selected"


class FitEvents:
    """Curve fitting events.
    
    Events for curve fitting operations and results.
    """
    FIT_COMPLETED = "fit.completed"
    FIT_APPLIED = "fit.applied"
    FIT_FAILED = "fit.failed"
    FIT_STARTED = "fit.started"


class ProjectEvents:
    """Project-related events.
    
    Generic project events that are item-type agnostic.
    Use these when components need broad project awareness.
    """
    # High-level project events
    PROJECT_CREATED = "project.created"
    PROJECT_LOADED = "project.loaded"
    PROJECT_SAVED = "project.saved"
    PROJECT_CLOSED = "project.closed"
    PROJECT_SAVING = "project.saving"
    FIRST_PROJECT_LOADED = "first_project_loaded"
    
    # Generic project structure events (item-type agnostic)
    PROJECT_CHANGED = "project.changed"  # Generic change event - use for broad awareness
    PROJECT_ITEM_ADDED = "project.item_added"  # Generic item added - use when type doesn't matter
    PROJECT_ITEM_REMOVED = "project.item_removed"  # Generic item removed
    PROJECT_ITEM_RENAMED = "project.item_renamed"  # Generic item renamed
    PROJECT_ITEM_MOVED = "project.item_moved"  # Generic item moved
    PROJECT_STRUCTURE_CHANGED = "project.structure_changed"  # Structure change - folders/items reorganized


class FolderEvents:
    """Folder-specific events.
    
    Use these events when components need specific folder operation details.
    """
    FOLDER_CREATED = "folder.created"
    FOLDER_RENAMED = "folder.renamed"
    FOLDER_DELETED = "folder.deleted"
    FOLDER_MOVED = "folder.moved"


class NoteEvents:
    """Note-specific events.
    
    Use these events when components need specific note operation details.
    """
    NOTE_CREATED = "note.created"
    NOTE_RENAMED = "note.renamed"
    NOTE_DELETED = "note.deleted"
    NOTE_MOVED = "note.moved"
    NOTE_CONTENT_CHANGED = "note.content_changed"


class DatasetItemEvents:
    """Dataset item-specific events.
    
    Use these events when components need specific dataset item operation details.
    These are different from DatasetEvents - these are for dataset items in project tree,
    while DatasetEvents are for dataset data operations.
    """
    DATASET_ITEM_CREATED = "dataset_item.created"
    DATASET_ITEM_IMPORTED = "dataset_item.imported"
    DATASET_ITEM_REMOVED = "dataset_item.removed"
    DATASET_ITEM_RENAMED = "dataset_item.renamed"
    DATASET_ITEM_MOVED = "dataset_item.moved"


class EventHierarchy:
    """Defines automatic event hierarchy mappings."""
    
    # Simple mapping from specific events to their parent chain
    HIERARCHY_MAP: Dict[str, List[str]] = {
        "app.closing": ["app.closing"],

        # Folder events
        "folder.created": ["folder.created", "project.item_added", "project.changed"],
        "folder.renamed": ["folder.renamed", "project.item_renamed", "project.changed"],
        "folder.deleted": ["folder.deleted", "project.item_removed", "project.changed"],
        "folder.moved": ["folder.moved", "project.item_moved", "project.changed"],
        
        # Note events
        "note.created": ["note.created", "project.item_added", "project.changed"],
        "note.renamed": ["note.renamed", "project.item_renamed", "project.changed"],
        "note.deleted": ["note.deleted", "project.item_removed", "project.changed"],
        "note.moved": ["note.moved", "project.item_moved", "project.changed"],
        "note.content_changed": ["note.content_changed", "project.changed"],
        
        # Dataset item events
        "dataset_item.created": ["dataset_item.created", "project.item_added", "project.changed"],
        "dataset_item.imported": ["dataset_item.imported", "project.item_added", "project.changed"],
        "dataset_item.removed": ["dataset_item.removed", "project.item_removed", "project.changed"],
        "dataset_item.renamed": ["dataset_item.renamed", "project.item_renamed", "project.changed"],
        "dataset_item.moved": ["dataset_item.moved", "project.item_moved", "project.changed"],
        
        # Dataset operation events
        "dataset.column_added": ["dataset.column_added", "dataset.structure_changed", "dataset.changed"],
        "dataset.column_removed": ["dataset.column_removed", "dataset.structure_changed", "dataset.changed"],
        "dataset.column_renamed": ["dataset.column_renamed", "dataset.structure_changed", "dataset.changed"],
        "dataset.column_reordered": ["dataset.column_reordered", "dataset.structure_changed", "dataset.changed"],
        "dataset.row_added": ["dataset.row_added", "dataset.structure_changed", "dataset.changed"],
        "dataset.row_removed": ["dataset.row_removed", "dataset.structure_changed", "dataset.changed"],
        "dataset.row_updated": ["dataset.row_updated", "dataset.data_changed", "dataset.changed"],
        "dataset.bulk_update": ["dataset.bulk_update", "dataset.data_changed", "dataset.changed"],
        "dataset.imported": ["dataset.imported", "dataset.changed"],
        "dataset.exported": ["dataset.exported"],
        
        # Analysis events
        "analysis.completed": ["analysis.completed", "dataset.column_added", "dataset.structure_changed", "dataset.changed"],
        "analysis.failed": ["analysis.failed"],
        "analysis.started": ["analysis.started"],
        "analysis.config_changed": ["analysis.config_changed"],
        
        # Chart events
        "chart.created": ["chart.created"],
        "chart.updated": ["chart.updated"],
        "chart.deleted": ["chart.deleted"],
        "chart.style_changed": ["chart.style_changed"],
        "chart.data_updated": ["chart.data_updated"],
        "chart.selected": ["chart.selected"],
        
        # UI events (no hierarchy needed)
        "ui.tab_changed": ["ui.tab_changed"],
        "ui.tab_created": ["ui.tab_created"],
        "ui.tab_closed": ["ui.tab_closed"],
        "ui.tab_title_changed": ["ui.tab_title_changed"],
        "ui.panel_visibility_changed": ["ui.panel_visibility_changed"],
        "ui.sidebar_panel_selected": ["ui.sidebar_panel_selected"],
        
        # Project events (already top-level)
        "project.created": ["project.created"],
        "project.loaded": ["project.loaded"],
        "project.saved": ["project.saved"],
        "project.closed": ["project.closed"],
        "project.saving": ["project.saving"],
        "first_project_loaded": ["first_project_loaded"],
        "project.changed": ["project.changed"],
        "project.item_added": ["project.item_added", "project.changed"],
        "project.item_removed": ["project.item_removed", "project.changed"],
        "project.item_renamed": ["project.item_renamed", "project.changed"],
        "project.item_moved": ["project.item_moved", "project.changed"],
        "project.structure_changed": ["project.structure_changed", "project.changed"],
    }
    
    @classmethod
    def get_hierarchy(cls, event_type: str) -> List[str]:
        """Get the event hierarchy for a given event type.
        
        Args:
            event_type: The specific event type to get hierarchy for
            
        Returns:
            List of event types from specific to generic
        """
        return cls.HIERARCHY_MAP.get(event_type, [event_type])
    
    @classmethod
    def add_mapping(cls, event_type: str, hierarchy: List[str]) -> None:
        """Add a new event hierarchy mapping (for extensions).
        
        Args:
            event_type: The specific event type
            hierarchy: List of event types from specific to generic
        """
        cls.HIERARCHY_MAP[event_type] = hierarchy
