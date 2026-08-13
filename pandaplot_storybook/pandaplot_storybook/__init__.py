"""pandaplot_storybook: a standalone PySide6 gallery for pandaplot's
reusable UI widgets.

pandaplot's root pyproject.toml declares no [build-system], so it isn't an
installable package -- this inserts the sibling `pandaplot/` source tree
onto sys.path so `import pandaplot....` resolves without pandaplot ever
depending on (or knowing about) this project.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
