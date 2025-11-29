"""Update entities for the Fronius Wattpilot integration."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import yaml
from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.const import (
    CONF_PARAMS,
    CONF_TIMEOUT,
)
from homeassistant.core import HomeAssistant
from packaging.version import Version

from .const import (
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .entities import ChargerPlatformEntity
from .utils import (
    GetChargerProp,
    async_SetChargerProp,
)

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .types import WattpilotConfigEntry

_LOGGER: Final = logging.getLogger(__name__)
PLATFORM = "update"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WattpilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the update platform."""
    _LOGGER.debug("Setting up %s platform entry: %s", PLATFORM, entry.entry_id)
    entities: list[ChargerUpdate] = []

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
            if "id_installed" not in entity_cfg or entity_cfg["id_installed"] is None:
                _LOGGER.error(
                    "%s - async_setup_entry %s: Invalid yaml configuration - no id_installed: %s",
                    entry.entry_id,
                    PLATFORM,
                    entity_cfg,
                )
                continue
            if "id_trigger" not in entity_cfg or entity_cfg["id_trigger"] is None:
                _LOGGER.error(
                    "%s - async_setup_entry %s: Invalid yaml configuration - no id_trigger: %s",
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
            entity = ChargerUpdate(hass, entry, entity_cfg, charger)
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


class ChargerUpdate(ChargerPlatformEntity, UpdateEntity):
    """Update class for Fronius Wattpilot integration."""

    _state_attr = "_attr_latest_version"
    _dummy_version = "0.0.1"
    _available_versions: dict[str, str] = {}

    def _init_platform_specific(self) -> None:
        """Platform specific init actions."""
        _LOGGER.debug(
            "%s - %s: _init_platform_specific", self._charger_id, self._identifier
        )
        self._identifier_installed = self._entity_cfg.get("id_installed")
        self._identifier_trigger = self._entity_cfg.get("id_trigger", None)
        self._identifier_status = self._entity_cfg.get("id_status", None)

        self._attr_installed_version = GetChargerProp(
            self._charger, self._identifier_installed, None
        )
        self._attr_latest_version = self._update_available_versions(
            None, return_latest=True
        )

        if self._identifier_trigger is not None:
            self._attr_supported_features |= UpdateEntityFeature.INSTALL
            self._attr_supported_features |= UpdateEntityFeature.SPECIFIC_VERSION
        _LOGGER.debug(
            "%s - %s: _init_platform_specific complete",
            self._charger_id,
            self._identifier,
        )

    def _update_available_versions(
        self, v_list: list[str] | str | None = None, return_latest: bool = False
    ) -> str | None:
        """Get the latest update version of available versions."""
        _LOGGER.debug(
            "%s - %s: _update_available_versions", self._charger_id, self._identifier
        )
        try:
            if v_list is None:
                v_list = GetChargerProp(self._charger, self._identifier, None)
            if (
                v_list is None
                and hasattr(self, "_attr_installed_version")
                and self._attr_installed_version is not None
            ):
                v_list = [self._attr_installed_version]
            elif v_list is None:
                v_list = [self._dummy_version]
            elif not isinstance(v_list, list):
                v_list = [v_list]
            self._available_versions = self._get_versions_dict(v_list)
            latest = list(self._available_versions.keys())
            latest.sort(key=Version)
            return latest[-1]
        except Exception as e:
            _LOGGER.error(
                "%s - %s: _update_available_versions failed: %s (%s.%s)",
                self._charger_id,
                self._identifier,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            if return_latest:
                return self._dummy_version
            return None

    def _get_versions_dict(self, v_list: list[str]) -> dict[str, str]:
        """Create a dict with clean and named versions."""
        _LOGGER.debug("%s - %s: _get_versions_dict", self._charger_id, self._identifier)
        try:
            versions: dict[str, str] = {}
            for v in v_list:
                c = (v.lower()).replace("x", "0")
                c = re.sub(
                    r"^(v|ver|vers|version)*\s*\.*\s*([0-9.x]*)\s*-?\s*((alpha|beta|dev|rc|post|a|b|release)+[0-9]*)?\s*.*$",
                    r"\2\3",
                    c,
                )
                versions[c] = v
            return versions
        except Exception as e:
            _LOGGER.error(
                "%s - %s: _get_versions_dict failed: %s (%s.%s)",
                self._charger_id,
                self._identifier,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )
            return {}

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Trigger update install."""
        try:
            _LOGGER.debug(
                "%s - %s: async_install: update charger to: %s",
                self._charger_id,
                self._identifier,
                version,
            )
            if version is None:
                version = self._attr_latest_version
            v_name = self._available_versions.get(version, None)
            if v_name is None:
                _LOGGER.error(
                    "%s - %s: async_install failed: version (%s) not in available: %s",
                    self._charger_id,
                    self._identifier,
                    version,
                    self._available_versions,
                )
                return
            _LOGGER.debug(
                "%s - %s: async_install: trigger charger update via: %s -> %s",
                self._charger_id,
                self._identifier,
                self._identifier_trigger,
                v_name,
            )
            await async_SetChargerProp(
                self._charger,
                self._identifier_trigger,
                v_name,
                force=True,
                force_type=self._set_type,
            )

            # Get timeout from config
            timeout = DEFAULT_TIMEOUT
            entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, None)
            if entry_data is not None:
                config_params = entry_data.get(CONF_PARAMS, None)
                if config_params is not None:
                    timeout = config_params.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            timeout = timeout * 4

            timer = 0
            while timeout > timer and self._charger.connected:
                await asyncio.sleep(1)
                timer += 1
            if self._charger.connected:
                _LOGGER.error(
                    "%s - %s: async_install: update timeout during update install: %s seconds",
                    self._charger_id,
                    self._identifier,
                    timeout,
                )
                return
            _LOGGER.debug(
                "%s - %s: async_install: charger disconnected - waiting for reconnect",
                self._charger_id,
                self._identifier,
            )
            timer = 0
            while timeout > timer and not self._charger.connected:
                await asyncio.sleep(1)
                timer += 1
            if not self._charger.connected:
                _LOGGER.error(
                    "%s - %s: async_install: update timeout during charger restart: %s seconds",
                    self._charger_id,
                    self._identifier,
                    timeout,
                )
                return
        except Exception as e:
            _LOGGER.error(
                "%s - %s: async_install failed: %s (%s.%s)",
                self._charger_id,
                self._identifier,
                str(e),
                e.__class__.__module__,
                type(e).__name__,
            )

    async def _async_update_validate_platform_state(
        self, state: Any = None
    ) -> str | None:
        """Async: Validate the given state for update specific requirements."""
        _LOGGER.debug(
            "%s - %s: _async_update_validate_platform_state",
            self._charger_id,
            self._identifier,
        )
        self._attr_installed_version = GetChargerProp(
            self._charger, self._identifier_installed, None
        )
        state = await self.hass.async_add_executor_job(
            self._update_available_versions, state, True
        )
        _LOGGER.debug(
            "%s - %s: _async_update_validate_platform_state: state: %s",
            self._charger_id,
            self._identifier,
            state,
        )
        return state
