"""Button entities for the Fronius Wattpilot integration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

import aiofiles
import yaml
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .entities import ChargerPlatformEntity
from .utils import async_SetChargerProp

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .types import WattpilotConfigEntry

_LOGGER: Final = logging.getLogger(__name__)
PLATFORM = "button"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WattpilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    _LOGGER.debug("Setting up %s platform entry: %s", PLATFORM, entry.entry_id)
    entities: list[ChargerButton] = []

    try:
        _LOGGER.debug(
            "%s - async_setup_entry %s: Reading static yaml configuration",
            entry.entry_id,
            PLATFORM,
        )
        yaml_path = Path(__file__).parent / f"{PLATFORM}.yaml"
        async with aiofiles.open(yaml_path) as y:
            yaml_cfg = yaml.safe_load(await y.read())
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry %s: Reading static yaml configuration failed: %s (%s.%s)",
            entry.entry_id,
            PLATFORM,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        return

    try:
        _LOGGER.debug(
            "%s - async_setup_entry %s: Getting charger instance from runtime_data",
            entry.entry_id,
            PLATFORM,
        )
        charger = entry.runtime_data.charger
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry %s: Getting charger instance from runtime_data failed: %s (%s.%s)",
            entry.entry_id,
            PLATFORM,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        return

    try:
        _LOGGER.debug(
            "%s - async_setup_entry %s: Getting push entities dict from runtime_data",
            entry.entry_id,
            PLATFORM,
        )
        push_entities = entry.runtime_data.push_entities
    except Exception as e:
        _LOGGER.error(
            "%s - async_setup_entry %s: Getting push entities dict from runtime_data failed: %s (%s.%s)",
            entry.entry_id,
            PLATFORM,
            str(e),
            e.__class__.__module__,
            type(e).__name__,
        )
        return

    for entity_cfg in yaml_cfg.get(PLATFORM, []):
        try:
            entity_cfg["source"] = "none"
            if "id" not in entity_cfg or entity_cfg["id"] is None:
                _LOGGER.error(
                    "%s - async_setup_entry %s: Invalid yaml configuration - no id: %s",
                    entry.entry_id,
                    PLATFORM,
                    entity_cfg,
                )
                continue
            if "source" not in entity_cfg or entity_cfg["source"] is None:
                _LOGGER.error(
                    "%s - async_setup_entry %s: Invalid yaml configuration - no source: %s",
                    entry.entry_id,
                    PLATFORM,
                    entity_cfg,
                )
                continue
            entity = ChargerButton(hass, entry, entity_cfg, charger)
            if entity is None:
                continue
            entities.append(entity)
            if entity._source == "property":
                push_entities[entity._identifier] = entity
            await asyncio.sleep(0)
        except Exception as e:
            _LOGGER.error(
                "%s - async_setup_entry %s: Reading static yaml configuration failed: %s (%s.%s)",
                entry.entry_id,
                PLATFORM,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return

    _LOGGER.info(
        "%s - async_setup_entry: setup %s %s entities",
        entry.entry_id,
        len(entities),
        PLATFORM,
    )
    if not entities:
        return
    async_add_entities(entities)


class ChargerButton(ChargerPlatformEntity, ButtonEntity):
    """Button class for Fronius Wattpilot integration."""

    def _init_platform_specific(self) -> None:
        """Platform specific init actions."""
        self._set_value = self._entity_cfg.get("set_value", None)
        if self._set_value is None:
            _LOGGER.error(
                "%s - %s: __init__: Required configuration option 'set_value' missing - please specify: %s",
                self._charger_id,
                self._identifier,
                self._set_value,
            )
            self._init_failed = True

    async def async_local_poll(self) -> None:
        """Async: Poll the latest data and states from the entity."""
        # No state required for ButtonEntity

    async def async_press(self) -> None:
        """Async: Handle button press."""
        try:
            await async_SetChargerProp(
                self._charger,
                self._identifier,
                self._set_value,
                force=True,
                force_type=self._set_type,
            )
        except Exception as e:
            _LOGGER.error(
                "%s - %s: update failed: %s (%s.%s)",
                self._charger_id,
                self._identifier,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
