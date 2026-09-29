"""Configuration manager for ghive settings."""

import json
from pathlib import Path
from typing import Any, Dict

CURRENT_CONFIG_VERSION = 1


class ConfigManager:
    """Manages persistent application configuration in ~/.ghive/config.json."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config_dir = Path.home() / ".ghive"
        self.config_file = self.config_dir / "config.json"

        default_clone_dir = str(Path.home() / "Documents" / "GitHub")

        self.settings: Dict[str, Any] = {
            "config_version": CURRENT_CONFIG_VERSION,
            "general": {
                "default_limit": 30,
                "auto_refresh_interval": 0,
                "default_clone_path": default_clone_dir,
                "active_repo": "",
            },
            "paths": {
                "gh": "",
                "git": "",
            },
            "confirmations": {
                "confirm_delete_repo": True,
                "confirm_delete_gist": True,
                "confirm_close_issue": True,
                "confirm_close_pr": True,
                "confirm_merge_pr": True,
            },
        }

        self.load()
        self._initialized = True

    def load(self) -> None:
        """Load configuration from disk, apply migrations and validation."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)

                loaded_version = loaded_settings.get("config_version", 0)
                if loaded_version < CURRENT_CONFIG_VERSION:
                    loaded_settings = self._migrate(loaded_settings, loaded_version)

                self._deep_merge(self.settings, loaded_settings)
            except Exception as e:
                print(f"[ConfigManager] Error reading config file: {e}")
        self._validate()

    def _migrate(self, settings: dict, from_version: int) -> dict:
        """Migrate configuration from older schemas."""
        if from_version < 1:
            settings.setdefault("general", {})
            settings["general"].setdefault("default_limit", 30)
            settings["config_version"] = 1
        return settings

    def _validate(self) -> None:
        """Validate loaded configuration and restore sensible defaults if corrupted."""
        general = self.settings.setdefault("general", {})
        limit = general.get("default_limit")
        if not isinstance(limit, int) or limit < 5 or limit > 200:
            general["default_limit"] = 30

        interval = general.get("auto_refresh_interval")
        if not isinstance(interval, (int, float)) or interval < 0 or interval > 3600:
            general["auto_refresh_interval"] = 0

        paths = self.settings.setdefault("paths", {})
        for key in ("gh", "git"):
            if not isinstance(paths.get(key), str):
                paths[key] = ""

        confs = self.settings.setdefault("confirmations", {})
        for key in (
            "confirm_delete_repo",
            "confirm_delete_gist",
            "confirm_close_issue",
            "confirm_close_pr",
            "confirm_merge_pr",
        ):
            if not isinstance(confs.get(key), bool):
                confs[key] = True

    def _deep_merge(self, base: dict, update: dict) -> None:
        """Recursively merge values from update into base."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def save(self) -> None:
        """Save settings to disk."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"[ConfigManager] Error saving config file: {e}")

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value."""
        return self.settings.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value and save."""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        self.save()
