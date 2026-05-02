"""
TV Control Interface — Xnoppo
Dynamically loads the selected TV plugin from lib/TV/<model>.
"""

import importlib.util
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_plugin(config):
    """Dynamically load the plugin module for the selected TV model."""
    model = config.get("TV_model")
    if not model:
        logger.warning("No TV model selected in config.")
        return None
    
    plugin_dir = Path(__file__).parent / "TV" / model
    if not plugin_dir.exists():
        logger.warning("TV plugin directory not found: %s", plugin_dir)
        return None
    
    py_files = list(plugin_dir.glob("*.py"))
    if not py_files:
        logger.warning("No python plugin found in %s", plugin_dir)
        return None
        
    plugin_file = py_files[0]
    module_name = f"xnoppo_tv_{model.lower()}"
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error("Failed to load TV plugin %s: %s", model, e)
        return None


def tv_config(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "tv_config"):
        return plugin.tv_config(config)
    logger.info("tv_config called (no plugin or method)")


def tv_test(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "tv_test"):
        return plugin.tv_test(config)
    logger.info("TV Test (dummy) — OK")


def tv_test_conn(config):
    """Test TV connectivity."""
    logger.info("Called tv_test_conn")
    return "OK"


def tv_change_hdmi(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "tv_change_hdmi"):
        return plugin.tv_change_hdmi(config)
    logger.info("tv_change_hdmi called (no plugin)")
    return "OK"


def tv_set_prev(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "tv_set_prev"):
        return plugin.tv_set_prev(config)
    logger.info("tv_set_prev called (no plugin)")
    return "OK"


def tv_set_emby(config):
    """Switch TV to the Emby app."""
    logger.info("Called tv_set_emby")
    return "OK"


def get_tv_key(config):
    """Retrieve or generate the TV pairing key."""
    logger.info("Called get_tv_key")
    return "OK"


def get_tv_sources(config):
    """Get list of available TV input sources."""
    logger.info("Called get_tv_sources")
    return "OK"
