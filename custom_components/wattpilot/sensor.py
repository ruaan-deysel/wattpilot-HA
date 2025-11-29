"""Sensor entities for the Fronius Wattpilot integration."""

from __future__ import annotations

import asyncio
import html
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import yaml
from homeassistant.components.sensor import (
    UNIT_CONVERTERS,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .entities import ChargerPlatformEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .types import WattpilotConfigEntry

_LOGGER: Final = logging.getLogger(__name__)
PLATFORM = "sensor"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WattpilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up %s platform entry: %s", PLATFORM, entry.entry_id)
    entities: list[ChargerSensor] = []

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

    for entity_cfg in yaml_cfg[PLATFORM]:
        try:
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
            entity = ChargerSensor(hass, entry, entity_cfg, charger)
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


class ChargerSensor(ChargerPlatformEntity, SensorEntity):
    """Sensor class for Fronius Wattpilot integration."""

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
        if self._entity_cfg.get("state_class", None) is not None:
            self._attr_state_class = SensorStateClass(
                (self._entity_cfg.get("state_class")).lower()
            )
        if self._entity_cfg.get("enum", None) is not None:
            self._state_enum = dict(self._entity_cfg.get("enum", None))
        if self._entity_cfg.get("html_unescape", None) is not None:
            self._html_unescape = True

    async def _async_update_validate_platform_state(
        self, state: Any = None
    ) -> Any | None:
        """Async: Validate the given state for sensor specific requirements."""
        try:
            if state is None or state == "None":
                state = STATE_UNKNOWN
            elif hasattr(self, "_html_unescape") and self._html_unescape:
                state = html.unescape(state)
            elif not hasattr(self, "_state_enum"):
                pass
            elif state in list(self._state_enum.keys()):
                state = self._state_enum[state]
            elif state in list(self._state_enum.values()):
                pass
            else:
                _LOGGER.warning(
                    "%s - %s: _async_update_validate_platform_state failed: state %s not within enum values: %s",
                    self._charger_id,
                    self._identifier,
                    state,
                    self._state_enum,
                )
            if self._attr_native_unit_of_measurement is not None:
                self._attr_native_value = state
            return state
        except Exception as e:
            _LOGGER.error(
                "%s - %s: _async_update_validate_platform_state failed: %s (%s.%s)",
                self._charger_id,
                self._identifier,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return None
