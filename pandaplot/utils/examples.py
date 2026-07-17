"""Discovery of bundled example projects (.pplot files under the examples/ directory)."""

import json
import logging
import zipfile
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class ExampleProject(TypedDict):
    name: str
    description: str
    path: str


def get_examples_dir() -> Path:
    """Return the repo-root examples/ directory (sibling of the pandaplot package)."""
    return Path(__file__).resolve().parent.parent.parent / "examples"


def discover_example_projects(examples_dir: Path | None = None) -> list[ExampleProject]:
    """Scan examples_dir for .pplot project files and read their name/description.

    Each .pplot file is a zip archive containing a project.json with "name" and
    "description" fields, so those are read directly from the file rather than
    kept as a separate, easily-stale hardcoded list.
    """
    if examples_dir is None:
        examples_dir = get_examples_dir()

    if not examples_dir.is_dir():
        return []

    examples: list[ExampleProject] = []
    for pplot_path in sorted(examples_dir.rglob("*.pplot")):
        try:
            with zipfile.ZipFile(pplot_path) as archive:
                project_meta = json.loads(archive.read("project.json"))
            examples.append({
                "name": project_meta.get("name", pplot_path.stem),
                "description": project_meta.get("description", ""),
                "path": str(pplot_path),
            })
        except Exception as e:  # noqa: BLE001
            logger.warning("Skipping unreadable example project '%s': %s", pplot_path, e)

    return examples
