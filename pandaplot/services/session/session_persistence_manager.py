"""Session Persistence Manager.

Remembers what was open (the current project, its open tabs, and which tab
was active) so the app can restore it on the next launch. Owns the mapping
between session concepts and the underlying ApplicationConfig fields, so
callers never need to know the config's raw dict shape - they call
``update_project``/``update_tabs``/``reset`` instead of building a mapping
and calling ``ConfigManager.update()`` directly.
"""
from __future__ import annotations

from typing import Optional

from pandaplot.services.config.config_manager import ConfigManager


class SessionPersistenceManager:
    """Persists and restores "what was open" across app launches."""

    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager

    # ----- reading back the remembered session ------------------------------
    @property
    def last_project_path(self) -> Optional[str]:
        return self._config_manager.config.last_project_path

    @property
    def last_open_tabs(self) -> list[str]:
        return list(self._config_manager.config.last_open_tabs)

    @property
    def last_active_tab_id(self) -> Optional[str]:
        return self._config_manager.config.last_active_tab_id

    # ----- recording session changes -----------------------------------------
    def update_project(self, file_path: Optional[str]) -> None:
        """Remember which project to reopen on next launch (None to forget)."""
        self._config_manager.update({"last_project_path": file_path}, save=True)

    def update_tabs(self, open_tabs: list[str], active_tab_id: Optional[str]) -> None:
        """Remember which tabs were open (and which was active) for next launch."""
        self._config_manager.update({
            "last_open_tabs": open_tabs,
            "last_active_tab_id": active_tab_id,
        }, save=True)

    def reset(self) -> None:
        """Forget the remembered project and tabs (e.g. on explicit project close)."""
        self._config_manager.update({
            "last_project_path": None,
            "last_open_tabs": [],
            "last_active_tab_id": None,
        }, save=True)


__all__ = ["SessionPersistenceManager"]
