"""
AV Receiver Control Interface — Xnoppo
Dynamically loads the selected AV receiver plugin from lib/AV/<model>.
"""

import importlib.util
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_plugin(config):
    """Dynamically load the plugin module for the selected AV model."""
    model = config.get("AV_model")
    if not model:
        logger.warning("No AV model selected in config.")
        return None
    
    # Plugin paths are like: lib/AV/YAMAHA/yamaha.py
    # But since we don't know the exact filename (it might be YAMAHA.py or yamaha.py),
    # we look for the first .py file in the directory that matches the model name (case-insensitive).
    plugin_dir = Path(__file__).parent / "AV" / model
    if not plugin_dir.exists():
        logger.warning("AV plugin directory not found: %s", plugin_dir)
        return None
    
    py_files = list(plugin_dir.glob("*.py"))
    if not py_files:
        logger.warning("No python plugin found in %s", plugin_dir)
        return None
        
    plugin_file = py_files[0]
    module_name = f"xnoppo_av_{model.lower()}"
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error("Failed to load AV plugin %s: %s", model, e)
        return None


def av_config(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "av_config"):
        return plugin.av_config(config)
    logger.info("av_config called (no plugin or method)")


def av_test(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "av_test"):
        return plugin.av_test(config)
    logger.info("AV Test (dummy) — OK")


def av_check_power(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "av_check_power"):
        return plugin.av_check_power(config)
    logger.info("av_check_power called (no plugin)")
    return "OK"


def av_change_hdmi(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "av_change_hdmi"):
        return plugin.av_change_hdmi(config)
    logger.info("av_change_hdmi called (no plugin)")
    return "OK"


def av_power_off(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "av_power_off"):
        return plugin.av_power_off(config)
    logger.info("av_power_off called (no plugin)")
    return "OK"


def av_get_current_input(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "av_get_current_input"):
        return plugin.av_get_current_input(config)
    return None


def av_set_input(config, input_str):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "av_set_input"):
        return plugin.av_set_input(config, input_str)
    return "OK"


def get_hdmi_list(config):
    plugin = _load_plugin(config)
    if plugin and hasattr(plugin, "get_hdmi_list"):
        return plugin.get_hdmi_list(config)
    logger.info("get_hdmi_list called (no plugin)")
    return None
