"""Switch entities for the Fronius Wattpilot integration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import yaml
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant

from .entities import ChargerPlatformEntity
from .utils import async_SetChargerProp

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .types import WattpilotConfigEntry

_LOGGER: Final = logging.getLogger(__name__)
PLATFORM = "switch"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WattpilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    _LOGGER.debug("Setting up %s platform entry: %s", PLATFORM, entry.entry_id)
    entities: list[ChargerSwitch] = []

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
            entity = ChargerSwitch(hass, entry, entity_cfg, charger)
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


class ChargerSwitch(ChargerPlatformEntity, SwitchEntity):
    """Switch class for Fronius Wattpilot integration."""

    async def _async_update_validate_platform_state(
        self, state: Any = None
    ) -> str | None:
        """Async: Validate the given state for switch specific requirements."""
        try:
            if str(state) in [STATE_ON, STATE_OFF, STATE_UNKNOWN]:
                pass
            elif str(state).lower() == "true":
                state = STATE_ON
            elif str(state).lower() == "false":
                state = STATE_OFF
            else:
                _LOGGER.warning(
                    "%s - %s: _async_update_validate_platform_state failed: state %s not valid for switch platform",
                    self._charger_id,
                    self._identifier,
                    state,
                )
                state = STATE_UNKNOWN

            if state == STATE_ON and self._entity_cfg.get("invert", False):
                _LOGGER.debug(
                    "%s - %s: _async_update_validate_platform_state: invert state: %s -> %s",
                    self._charger_id,
                    self._identifier,
                    STATE_ON,
                    STATE_OFF,
                )
                state = STATE_OFF
            elif state == STATE_OFF and self._entity_cfg.get("invert", False):
                _LOGGER.debug(
                    "%s - %s: _async_update_validate_platform_state: invert state: %s -> %s",
                    self._charger_id,
                    self._identifier,
                    STATE_OFF,
                    STATE_ON,
                )
                state = STATE_ON
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

    @property
    def is_on(self) -> bool:
        """Return true if entity is on."""
        return self.state == STATE_ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Async: Turn entity on."""
        try:
            _LOGGER.debug(
                "%s - %s: async_turn_on: %s",
                self._charger_id,
                self._identifier,
                self._attr_name,
            )
            value = not self._entity_cfg.get("invert", False)
            await async_SetChargerProp(self._charger, self._identifier, value)
        except Exception as e:
            _LOGGER.error(
                "%s - %s: async_turn_on failed: %s (%s.%s)",
                self._charger_id,
                self._identifier,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Async: Turn entity off."""
        try:
            _LOGGER.debug(
                "%s - %s: async_turn_off: %s",
                self._charger_id,
                self._identifier,
                self._attr_name,
            )
            value = self._entity_cfg.get("invert", False)
            await async_SetChargerProp(self._charger, self._identifier, value)
        except Exception as e:
            _LOGGER.error(
                "%s - %s: async_turn_off failed: %s (%s.%s)",
                self._charger_id,
                self._identifier,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
