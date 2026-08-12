"""PButton: a QPushButton with a semantic role (color) and shape (icon vs
standard), both applied as Qt dynamic properties consumed by
ThemeManager's global QSS (see [secondary]/[destructive]/[primary]/[iconButton]
selectors in pandaplot/services/theme/theme_manager.py).
"""
from __future__ import annotations

from typing import Literal, Optional

from PySide6.QtWidgets import QPushButton, QWidget

ButtonRole = Literal["primary", "secondary", "destructive"]

_ROLES: tuple[ButtonRole, ...] = ("primary", "secondary", "destructive")


class PButton(QPushButton):
    def __init__(self, text: str = "", role: ButtonRole = "secondary",
                 icon: bool = False, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setProperty("iconButton", icon)
        self.set_role(role)

    def set_role(self, role: ButtonRole) -> None:
        for r in _ROLES:
            self.setProperty(r, r == role)
        self.style().unpolish(self)
        self.style().polish(self)
