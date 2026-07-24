"""
Dataset model for managing data table items in the project.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from pandaplot.models.project.items.item import Item


class Dataset(Item):
    """
    Represents a dataset item in the project.

    A dataset contains tabular data (typically from CSV or other data sources).
    It's part of the hierarchical project structure.

    Each column also gets a stable id (independent of its display name) so that
    charts/fits can reference a column by id and survive renames without having
    their stored column names rewritten. The id<->name mapping lives here, on
    the dataset that owns the column, and is kept in sync with ``data.columns``.
    """

    def __init__(self, id: Optional[str] = None, name: str = "",
                 data: Optional[pd.DataFrame] = None, source_file: Optional[str] = None,
                 column_ids: Optional[Dict[str, str]] = None):
        super().__init__(id, name)

        # Set dataset-specific attributes
        self.data: pd.DataFrame = data if data is not None else pd.DataFrame()
        self.source_file: Optional[str] = source_file
        # Maps current column name -> stable column id.
        self.column_ids: Dict[str, str] = dict(column_ids) if column_ids else {}
        self.ensure_column_ids()

    def set_data(self, data: pd.DataFrame) -> None:
        """Set the dataset data and update metadata."""
        self.data = data
        self.ensure_column_ids()
        self.update_modified_time()

    # -- Column id management -------------------------------------------------

    def ensure_column_ids(self) -> None:
        """Sync ``column_ids`` with the current DataFrame columns.

        Assigns a new stable id to any column that lacks one and drops entries
        for columns that no longer exist. Safe to call repeatedly.
        """
        if self.data is None:
            return
        current = [str(c) for c in self.data.columns]
        current_set = set(current)
        # Drop ids for columns that are gone.
        for name in list(self.column_ids.keys()):
            if name not in current_set:
                del self.column_ids[name]
        # Assign ids for new columns.
        for name in current:
            if name not in self.column_ids:
                self.column_ids[name] = uuid.uuid4().hex

    def get_column_id(self, name: str) -> Optional[str]:
        """Return the stable id for a column name, or None if unknown."""
        if not name:
            return None
        return self.column_ids.get(name)

    def get_column_name(self, column_id: str) -> Optional[str]:
        """Return the current name for a column id, or None if unknown."""
        if not column_id:
            return None
        for name, cid in self.column_ids.items():
            if cid == column_id:
                return name
        return None

    def rename_column(self, old_name: str, new_name: str) -> Optional[str]:
        """Rename a column in the DataFrame and remap its id.

        The column keeps its stable id, so references by id stay valid without
        being rewritten. Returns the column id, or None if the column is unknown.
        """
        if self.data is None or old_name not in self.column_ids:
            return None
        self.data.rename(columns={old_name: new_name}, inplace=True)
        column_id = self.column_ids.pop(old_name)
        self.column_ids[new_name] = column_id
        return column_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataset to dictionary for serialization."""
        data = super().to_dict()
        data.update({
            "source_file": self.source_file,
            "has_data": self.data is not None,
            "column_ids": self.column_ids,
        })

        # TODO: serialization of dataframe
        # Note: We don't serialize the actual DataFrame data here
        # Data should be stored separately or reconstructed from source
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dataset":
        """Create dataset from dictionary."""
        dataset = cls(
            id=data.get("id"),
            name=data.get("name", ""),
            source_file=data.get("source_file"),
            column_ids=data.get("column_ids"),
        )

        # Set inherited attributes
        dataset.parent_id = data.get("parent_id")
        dataset.created_at = data.get("created_at", datetime.now().isoformat())
        dataset.modified_at = data.get("modified_at", dataset.created_at)

        return dataset


def resolve_column_name(dataset: "Dataset", column_id: str, fallback_name: str) -> str:
    """Resolve a column reference to its current name.

    Prefers the stable ``column_id`` (following renames automatically) and
    falls back to ``fallback_name`` for references that predate column ids.
    """
    if column_id:
        name = dataset.get_column_name(column_id)
        if name is not None:
            return name
    return fallback_name
