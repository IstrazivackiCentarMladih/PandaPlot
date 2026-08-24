"""Application/window icon: the panda face used in the About dialog, as a static asset."""
from pathlib import Path

from PySide6.QtGui import QIcon

_ICON_PATH = Path(__file__).parent / "icons" / "app_icon.png"


def create_app_icon() -> QIcon:
    """Load the panda app icon from its asset file."""
    return QIcon(str(_ICON_PATH))
