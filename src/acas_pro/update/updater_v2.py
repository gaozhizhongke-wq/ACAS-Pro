"""ACAS Pro - Updater v2"""
from typing import Dict, Any, Tuple, Optional

from ..core.config_v2 import AppConfig


class UpdateManager:
    """Update manager - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self._current_version = "2.0.0"
        self._latest_version = "2.0.0"
    
    def check_update(self) -> Tuple[bool, Dict[str, Any]]:
        """Check for updates"""
        has_update = self._latest_version > self._current_version
        return True, {
            "has_update": has_update,
            "current_version": self._current_version,
            "latest_version": self._latest_version
        }
    
    def get_version(self) -> str:
        """Get current version"""
        return self._current_version
