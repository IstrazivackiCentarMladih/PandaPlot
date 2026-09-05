"""Version snapshot data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class VersionSnapshot:
    """Represents a saved snapshot/version of a project or document item."""

    version_id: str
    version_type: str  # "project" or "item"
    created_at: str  # ISO format string
    label: str
    item_id: Optional[str] = None  # None for project-level snapshots
    data: Dict[str, Any] = field(default_factory=dict)  # Serialized snapshot payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "version_type": self.version_type,
            "created_at": self.created_at,
            "label": self.label,
            "item_id": self.item_id,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VersionSnapshot":
        return cls(
            version_id=d["version_id"],
            version_type=d["version_type"],
            created_at=d["created_at"],
            label=d["label"],
            item_id=d.get("item_id"),
            data=d.get("data", {}),
        )
