"""Diagnostics support for the Fronius Wattpilot integration."""

from __future__ import annotations

import logging
from typing import (
    Any,
    Final,
)

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant
from importlib_metadata import version

from .const import (
    CONF_SERIAL,
)
from .types import WattpilotConfigEntry
from .utils import (
    wattpilot,
)

REDACT_CONFIG = {CONF_IP_ADDRESS, CONF_PASSWORD, CONF_SERIAL}
REDACT_ALLPROPS = {"wifis", "scan", "data", "dll", "cak", "ocppck", "ocppcc", "ocppsc"}

_LOGGER: Final = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: WattpilotConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    _LOGGER.debug("%s - diagnostics: Returning diagnostics", entry.entry_id)

    diag: dict[str, Any] = {}

    # Add config entry configuration
    try:
        _LOGGER.debug(
            "%s - diagnostics: Add config entry configuration to output",
            entry.entry_id,
        )
        diag["config"] = async_redact_data(entry.as_dict(), REDACT_CONFIG)
    except Exception as e:
        _LOGGER.error(
            "%s - diagnostics: Adding config entry configuration failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )

    # Add charger properties from runtime_data
    try:
        _LOGGER.debug(
            "%s - diagnostics: Add charger properties to output",
            entry.entry_id,
        )
        charger = entry.runtime_data.charger
        if charger and hasattr(charger, "allProps"):
            diag["charger_properties"] = async_redact_data(
                charger.allProps, REDACT_ALLPROPS
            )
        else:
            diag["charger_properties"] = "Charger not available or not initialized"
    except Exception as e:
        _LOGGER.error(
            "%s - diagnostics: Adding charger properties failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )

    # Add charger info
    try:
        charger = entry.runtime_data.charger
        if charger:
            diag["charger_info"] = {
                "connected": getattr(charger, "connected", None),
                "allPropsInitialized": getattr(charger, "allPropsInitialized", None),
                "name": getattr(charger, "name", None),
                "serial": async_redact_data(
                    {"serial": getattr(charger, "serial", None)}, {"serial"}
                ),
                "firmware": getattr(charger, "firmware", None),
            }
    except Exception as e:
        _LOGGER.error(
            "%s - diagnostics: Adding charger info failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )

    # Add python modules versions
    try:
        _LOGGER.debug(
            "%s - diagnostics: Add python modules version",
            entry.entry_id,
        )
        diag["modules"] = {
            "wattpilot_version": version("wattpilot"),
            "wattpilot_file": wattpilot.__file__,
            "pyyaml": version("pyyaml"),
            "importlib_metadata": version("importlib_metadata"),
            "aiofiles": version("aiofiles"),
            "packaging": version("packaging"),
        }
    except Exception as e:
        _LOGGER.error(
            "%s - diagnostics: Add python modules version failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )

    return diag
