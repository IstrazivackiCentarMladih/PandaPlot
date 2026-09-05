"""Version manager for creating, storing, listing, and restoring version snapshots."""

import copy
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pandaplot.models.project.items import Chart, Dataset, ImageGallery, Note
from pandaplot.models.versioning.version_snapshot import VersionSnapshot


class VersionManager:
    """Manages creation, storage, and retrieval of version snapshots for projects and items."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # Store snapshots in memory; per project/item ID
        self._snapshots: List[VersionSnapshot] = []

    def create_project_snapshot(self, project: Any, label: str = "Project Snapshot") -> VersionSnapshot:
        """Create a version snapshot of an entire project."""
        snapshot_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Serialize project state
        project_dict = project.to_dict()
        # Ensure datasets inside project store dataframes
        for item in project.get_all_items():
            if isinstance(item, Dataset) and hasattr(item, "data") and item.data is not None:
                # Store dataframe dict mapping under item id
                if "items" in project_dict:
                    for item_data in project_dict["items"]:
                        if item_data.get("id") == item.id:
                            item_data["_df_dict"] = item.data.to_dict(orient="list")

        snapshot = VersionSnapshot(
            version_id=snapshot_id,
            version_type="project",
            created_at=timestamp,
            label=label,
            item_id=None,
            data=copy.deepcopy(project_dict),
        )
        self._snapshots.append(snapshot)
        self.logger.info("Created project snapshot '%s' (%s)", label, snapshot_id)
        return snapshot

    def create_item_snapshot(self, item: Any, label: str = "Item Snapshot") -> VersionSnapshot:
        """Create a version snapshot of a specific item (Chart, Dataset, Note, etc.)."""
        snapshot_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        item_dict = item.to_dict()
        # For dataset, additionally capture dataframe data if applicable
        if isinstance(item, Dataset) and hasattr(item, "data") and item.data is not None:
            item_dict["_df_dict"] = item.data.to_dict(orient="list")

        snapshot = VersionSnapshot(
            version_id=snapshot_id,
            version_type="item",
            created_at=timestamp,
            label=label,
            item_id=item.id,
            data=copy.deepcopy(item_dict),
        )
        self._snapshots.append(snapshot)
        self.logger.info("Created item snapshot '%s' for item %s (%s)", label, item.id, snapshot_id)
        return snapshot

    def get_snapshots_for_project(self) -> List[VersionSnapshot]:
        """Return all project-level snapshots."""
        return [s for s in self._snapshots if s.version_type == "project"]

    def get_snapshots_for_item(self, item_id: str) -> List[VersionSnapshot]:
        """Return all snapshots for a given item ID."""
        return [s for s in self._snapshots if s.version_type == "item" and s.item_id == item_id]

    def get_snapshot(self, version_id: str) -> Optional[VersionSnapshot]:
        """Retrieve a specific snapshot by its version_id."""
        for s in self._snapshots:
            if s.version_id == version_id:
                return s
        return None

    def clear_snapshots(self) -> None:
        """Clear all snapshots."""
        self._snapshots.clear()
