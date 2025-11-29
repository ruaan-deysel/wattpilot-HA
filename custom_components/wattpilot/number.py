"""Number entities for the Fronius Wattpilot integration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import yaml
from homeassistant.components.number import (
    UNIT_CONVERTERS,
    NumberEntity,
)
from homeassistant.core import HomeAssistant

from .entities import ChargerPlatformEntity
from .utils import async_SetChargerProp

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .types import WattpilotConfigEntry

_LOGGER: Final = logging.getLogger(__name__)
PLATFORM = "number"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WattpilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    _LOGGER.debug("Setting up %s platform entry: %s", PLATFORM, entry.entry_id)
    entities: list[ChargerNumber] = []

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
            entity_cfg["source"] = "property"
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
            entity = ChargerNumber(hass, entry, entity_cfg, charger)
            if getattr(entity, "_init_failed", True):
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


class ChargerNumber(ChargerPlatformEntity, NumberEntity):
    """Number class for Fronius Wattpilot integration."""

    _state_attr = "_attr_native_value"

    def _init_platform_specific(self) -> None:
        """Platform specific init actions."""
        self._attr_native_unit_of_measurement = self._entity_cfg.get(
            "unit_of_measurement", None
        )
        unit_converter = UNIT_CONVERTERS.get(self._attr_device_class)
        if (
            unit_converter is not None
            and self._attr_native_unit_of_measurement in unit_converter.VALID_UNITS
        ):
            self._attr_suggested_unit_of_measurement = self._entity_cfg.get(
                "unit_of_measurement", None
            )

        n = self._entity_cfg.get("native_min_value", None)
        if n is not None:
            self._attr_native_min_value = float(n)
        n = self._entity_cfg.get("native_max_value", None)
        if n is not None:
            self._attr_native_max_value = float(n)
        n = self._entity_cfg.get("native_step", None)
        if n is not None:
            self._attr_native_step = float(n)
        self._attr_mode = self._entity_cfg.get("mode", None)

    def _get_platform_specific_state(self) -> Any:
        """Platform specific init actions."""
        return self.state

    async def _async_update_validate_platform_state(self, state: Any = None) -> Any:
        """Async: Validate the given state for sensor specific requirements."""
        if self._attr_native_unit_of_measurement is not None:
            self._attr_native_value = state
        return state

    async def async_set_native_value(self, value: float) -> None:
        """Async: Change the current value."""
        try:
            _LOGGER.debug(
                "%s - %s: async_set_native_value: value was changed to: %s",
                self._charger_id,
                self._identifier,
                value,
            )
            if self._identifier == "fte":
                _LOGGER.debug(
                    "%s - %s: async_set_native_value: apply ugly workaround to always set next trip distance to kWH instead of KM",
                    self._charger_id,
                    self._identifier,
                )
                await async_SetChargerProp(self._charger, "esk", True)
            await async_SetChargerProp(
                self._charger, self._identifier, value, force_type=self._set_type
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
