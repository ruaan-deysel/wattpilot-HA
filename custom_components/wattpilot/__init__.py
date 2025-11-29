"""Init for the Fronius Wattpilot integration."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.loader import async_get_integration

from .const import (
    DOMAIN,
    SUPPORTED_PLATFORMS,
)
from .services import (
    async_registerService,
    async_service_DisconnectCharger,
    async_service_ReConnectCharger,
    async_service_SetDebugProperties,
    async_service_SetGoECloud,
    async_service_SetNextTrip,
)
from .types import WattpilotConfigEntry, WattpilotRuntimeData
from .utils import (
    PropertyUpdateHandler,
    async_ConnectCharger,
    async_DisconnectCharger,
    wattpilot,
)

_LOGGER: Final = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: WattpilotConfigEntry) -> bool:
    """Set up a charger from the config entry."""
    _LOGGER.debug("Setting up config entry: %s", entry.entry_id)

    try:
        integration = await async_get_integration(hass, DOMAIN)
        version = integration.version
        if version:
            _LOGGER.debug(
                "%s - async_setup_entry: %s integration version: %s",
                entry.entry_id,
                DOMAIN,
                version,
            )
        else:
            _LOGGER.debug(
                "%s - async_setup_entry: Unknown %s integration version",
                entry.entry_id,
                DOMAIN,
            )
    except Exception:
        _LOGGER.warning(
            "%s - async_setup_entry: Unable to determine %s integration version",
            entry.entry_id,
            DOMAIN,
        )

    # Connect to the charger
    try:
        _LOGGER.debug("%s - async_setup_entry: Connecting charger", entry.entry_id)
        charger = await async_ConnectCharger(entry.entry_id, entry.data)
        if not charger:
            raise ConfigEntryNotReady(
                f"Failed to connect to charger for entry {entry.entry_id}"
            )
    except ConfigEntryNotReady:
        raise
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry: Connecting charger failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        raise ConfigEntryNotReady(f"Failed to connect to charger: {e}") from e

    # Set up runtime data using the modern pattern
    try:
        _LOGGER.debug(
            "%s - async_setup_entry: Creating runtime data",
            entry.entry_id,
        )
        entry.runtime_data = WattpilotRuntimeData(
            charger=charger,
            push_entities={},
            params=dict(entry.data),
            debug_properties=False,
        )
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry: Creating runtime data failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        await async_DisconnectCharger(entry.entry_id, charger)
        raise ConfigEntryNotReady(f"Failed to create runtime data: {e}") from e

    # Register option updates listener
    try:
        _LOGGER.debug(
            "%s - async_setup_entry: Register option updates listener",
            entry.entry_id,
        )
        entry.runtime_data.options_update_listener = entry.add_update_listener(
            options_update_listener
        )
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry: Register option updates listener failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        await async_DisconnectCharger(entry.entry_id, charger)
        raise ConfigEntryNotReady(
            f"Failed to register option updates listener: {e}"
        ) from e

    # Forward setup to platforms
    try:
        _LOGGER.debug(
            "%s - async_setup_entry: Trigger setup for platforms",
            entry.entry_id,
        )
        await hass.config_entries.async_forward_entry_setups(entry, SUPPORTED_PLATFORMS)
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry: Setup trigger failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        await async_DisconnectCharger(entry.entry_id, charger)
        raise ConfigEntryNotReady(f"Failed to setup platforms: {e}") from e

    # Register property update handler
    try:
        _LOGGER.debug(
            "%s - async_setup_entry: register properties update handler",
            entry.entry_id,
        )
        if hasattr(charger, "register_property_callback") and callable(
            charger.register_property_callback
        ):
            charger.register_property_callback(
                lambda identifier, value: PropertyUpdateHandler(
                    hass, entry.entry_id, identifier, value
                )
            )
        elif hasattr(charger, "add_event_handler") and callable(
            charger.add_event_handler
        ):
            entry.runtime_data.property_updates_callback = (
                lambda _, identifier, value: PropertyUpdateHandler(
                    hass, entry.entry_id, identifier, value
                )
            )
            charger.add_event_handler(
                wattpilot.Event.WP_PROPERTY,
                entry.runtime_data.property_updates_callback,
            )
        else:
            _LOGGER.warning(
                "%s - async_setup_entry: charger does not provide properties updater handler",
                entry.entry_id,
            )
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry: Could not register properties updater handler: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        await async_DisconnectCharger(entry.entry_id, charger)
        raise ConfigEntryNotReady(
            f"Failed to register property update handler: {e}"
        ) from e

    # Register services
    try:
        _LOGGER.debug("%s - async_setup_entry: register services", entry.entry_id)
        await async_registerService(
            hass, "disconnect_charger", async_service_DisconnectCharger
        )
        await async_registerService(
            hass, "reconnect_charger", async_service_ReConnectCharger
        )
        await async_registerService(hass, "set_goe_cloud", async_service_SetGoECloud)
        await async_registerService(
            hass, "set_debug_properties", async_service_SetDebugProperties
        )
        await async_registerService(hass, "set_next_trip", async_service_SetNextTrip)
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry: register services failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        await async_DisconnectCharger(entry.entry_id, charger)
        raise ConfigEntryNotReady(f"Failed to register services: {e}") from e

    _LOGGER.debug("%s - async_setup_entry: Completed", entry.entry_id)
    return True


async def options_update_listener(
    hass: HomeAssistant, entry: WattpilotConfigEntry
) -> None:
    """Handle options update."""
    try:
        _LOGGER.debug(
            "%s - options_update_listener: update options and reload config entry",
            entry.entry_id,
        )

        _LOGGER.debug("%s - options_update_listener: set new options", entry.entry_id)
        entry.runtime_data.params = dict(entry.options)
        hass.config_entries.async_update_entry(entry, data=entry.options)

        _LOGGER.debug(
            "%s - options_update_listener: async_reload entry", entry.entry_id
        )
        await hass.config_entries.async_reload(entry.entry_id)
    except Exception as e:
        _LOGGER.error(
            "%s - options_update_listener: update options failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )


async def async_unload_entry(hass: HomeAssistant, entry: WattpilotConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        _LOGGER.debug("Unloading config entry: %s", entry.entry_id)

        # Unload all platforms using the modern helper
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, SUPPORTED_PLATFORMS
        )

        if unload_ok:
            # Unload option updates listener
            _LOGGER.debug(
                "%s - async_unload_entry: Unload option updates listener",
                entry.entry_id,
            )
            if entry.runtime_data.options_update_listener:
                entry.runtime_data.options_update_listener()

            charger = entry.runtime_data.charger

            # Remove registered event handlers
            try:
                _LOGGER.debug(
                    "%s - async_unload_entry: remove registered event handlers",
                    entry.entry_id,
                )
                if hasattr(charger, "unregister_property_callback") and callable(
                    charger.unregister_property_callback
                ):
                    charger.unregister_property_callback()
                elif hasattr(charger, "remove_event_handler") and callable(
                    charger.remove_event_handler
                ):
                    charger.remove_event_handler(
                        wattpilot.Event.WP_PROPERTY,
                        entry.runtime_data.property_updates_callback,
                    )
            except Exception as e:
                _LOGGER.error(
                    "%s - async_unload_entry: failed to remove event handlers: %s (%s.%s)",
                    entry.entry_id,
                    str(e),
                    e.__class__.__module__,
                    type(e).__name__,
                )

            # Disconnect charger
            try:
                await async_DisconnectCharger(entry.entry_id, charger)
            except Exception as e:
                _LOGGER.error(
                    "%s - async_unload_entry: could not disconnect charger: %s (%s.%s)",
                    entry.entry_id,
                    str(e),
                    e.__class__.__module__,
                    type(e).__name__,
                )
                _LOGGER.error(
                    "%s - async_unload_entry: session at charger %s (%s) stays open -> restart charger",
                    entry.entry_id,
                    charger.name,
                    charger.serial,
                )

        return unload_ok

    except Exception as e:
        _LOGGER.error(
            "%s - async_unload_entry: Unload device failed: %s (%s.%s)",
            entry.entry_id,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        return False
