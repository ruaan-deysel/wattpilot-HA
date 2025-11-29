"""Select entities for the Fronius Wattpilot integration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import yaml
from homeassistant.components.select import SelectEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .entities import ChargerPlatformEntity
from .utils import async_SetChargerProp

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .types import WattpilotConfigEntry

_LOGGER: Final = logging.getLogger(__name__)
PLATFORM = "select"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WattpilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    _LOGGER.debug("Setting up %s platform entry: %s", PLATFORM, entry.entry_id)
    entities: list[ChargerSelect] = []

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
            entity = ChargerSelect(hass, entry, entity_cfg, charger)
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


class ChargerSelect(ChargerPlatformEntity, SelectEntity):
    """Select class for Fronius Wattpilot integration."""

    _state_attr = "_attr_current_option"

    def _init_platform_specific(self) -> None:
        """Platform specific init actions."""
        self._opt_identifier = self._entity_cfg.get("options", None)
        if isinstance(self._opt_identifier, dict):
            self._opt_dict = self._opt_identifier
        else:
            self._opt_dict = getattr(
                self._charger, self._opt_identifier, list(STATE_UNKNOWN)
            )
        if self._opt_dict != STATE_UNKNOWN:
            self._attr_options = list(self._opt_dict.values())

    async def _async_update_validate_platform_state(
        self, state: Any = None
    ) -> str | None:
        """Async: Validate the given state for select specific requirements."""
        try:
            if state in list(self._opt_dict.keys()):
                state = self._opt_dict[state]
            elif state in list(self._opt_dict.values()):
                pass
            else:
                _LOGGER.error(
                    "%s - %s: _async_update_validate_platform_state failed: state %s not within options_id values: %s",
                    self._charger_id,
                    self._identifier,
                    state,
                    self._opt_dict,
                )
                state = STATE_UNKNOWN
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

    async def async_select_option(self, option: str) -> None:
        """Async: Change the selected option."""
        try:
            key = list(self._opt_dict.keys())[
                list(self._opt_dict.values()).index(option)
            ]
            if key is None:
                _LOGGER.error(
                    "%s - %s: async_select_option: option %s not within options_id keys: %s",
                    self._charger_id,
                    self._identifier,
                    option,
                    self._opt_dict,
                )
                return
            _LOGGER.debug(
                "%s - %s: async_select_option: save option key %s",
                self._charger_id,
                self._identifier,
                key,
            )
            await async_SetChargerProp(
                self._charger, self._identifier, key, force_type=self._set_type
            )
        except Exception as e:
            _LOGGER.error(
                "%s - %s: async_select_option failed: %s (%s.%s)",
                self._charger_id,
                self._identifier,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
