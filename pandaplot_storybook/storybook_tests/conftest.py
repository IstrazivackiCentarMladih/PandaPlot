import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pandaplot_storybook import registry


@pytest.fixture(autouse=True)
def _isolate_story_registry():
    """Snapshot and restore the module-global story registry around each test.

    Without this, a test that registers a fake story (e.g. via `@story(...)`)
    would leak that registration into every test that runs afterwards, since
    `_registry` is a single module-global dict shared across the whole
    process.
    """
    snapshot = dict(registry._registry)
    try:
        yield
    finally:
        registry._registry.clear()
        registry._registry.update(snapshot)
