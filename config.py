"""
Xnoppo Configuration Manager
Handles loading, saving, and validating config.json with sensible defaults.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

VERSION = "3.00"

# Default values for all config keys
DEFAULTS = {
    "emby_server": "http://localhost:8096",
    "user_name": "",
    "user_password": "",
    "output_path": "backup",
    "Oppo_IP": "192.168.1.141",
    "timeout_oppo_conection": 10,
    "timeout_oppo_playitem": 60,
    "timeout_oppo_mount": 60,
    "Autoscript": False,
    "Always_ON": False,
    "TV": False,
    "TV_IP": "",
    "TV_KEY": "",
    "TV_DeviceName": "",
    "TV_model": "",
    "TV_SOURCES": [],
    "TV_script_init": "",
    "TV_script_end": "",
    "Source": 0,
    "DebugLevel": 0,
    "AV": False,
    "AV_Ip": "",
    "AV_Input": "",
    "AV_Always_ON": False,
    "AV_model": "",
    "AV_SOURCES": [],
    "AV_Port": 23,
    "AV_CMD_POW_ON": "cmd",
    "AV_CMD_CHANGE_HDMI": "cmd",
    "AV_CMD_POW_OFF": "cmd",
    "av_delay_hdmi": 0,
    "MonitoredDevice": "",
    "enable_all_libraries": False,
    "language": "es-ES",
    "default_nfs": False,
    "wait_nfs": False,
    "refresh_time": 5,
    "check_beta": False,
    "smbtrick": False,
    "BRDisc": False,
    "resume_on": "",
    "servers": [],
    "Libraries": [],
}


class XnoppoConfig:
    """Manages Xnoppo configuration with defaults and persistence."""

    def __init__(self, data: dict, config_path: Path):
        self._data = data
        self._config_path = config_path
        self._ws_client = None # Real private attribute, not in _data

    @classmethod
    def load(cls, config_path: str | Path) -> "XnoppoConfig":
        """Load config from JSON file, applying defaults for missing keys."""
        config_path = Path(config_path)
        if not config_path.exists():
            logger.warning("Config file not found at %s, using defaults", config_path)
            data = dict(DEFAULTS)
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Apply defaults for any missing keys
            for key, default_val in DEFAULTS.items():
                if key not in data:
                    data[key] = default_val

        config = cls(data, config_path)

        # Hard reset for the '36' length bug
        if config._data.get("MonitoredDevice") == "36":
            logger.warning("Corrupted MonitoredDevice='36' detected. Clearing it.")
            config._data["MonitoredDevice"] = ""
            config.save()

        # Migrate legacy string booleans to actual booleans
        for bool_key in ("TV", "AV"):
            if isinstance(config._data.get(bool_key), str):
                config._data[bool_key] = config._data[bool_key].lower() == "true"

        config._data["Version"] = VERSION

        # Ensure servers have Test_OK field
        for server in data.get("servers", []):
            server.setdefault("Test_OK", False)

        logger.info("Configuration loaded from %s", config_path)
        return cls(data, config_path)

    def save(self, path: str | Path | None = None):
        """Save config to JSON file."""
        save_path = Path(path) if path else self._config_path
        # Don't save transient keys
        save_data = {
            k: v for k, v in self._data.items()
            if k not in ("tv_dirs", "av_dirs", "langs", "devices")
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=4, ensure_ascii=False)
        logger.info("Configuration saved to %s", save_path)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def to_dict(self) -> dict:
        """Return a copy of the config as a plain dictionary."""
        return dict(self._data)

    def update(self, new_data: dict):
        """Update config with new data from the frontend."""
        self._data.update(new_data)

    def set_ws_client(self, client):
        self._ws_client = client

    def get_ws_client(self):
        return self._ws_client

    @staticmethod
    def get_version() -> str:
        return VERSION
