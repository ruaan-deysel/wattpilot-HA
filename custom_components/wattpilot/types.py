"""Type definitions for the Fronius Wattpilot integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .entities import ChargerPlatformEntity


@dataclass
class WattpilotRuntimeData:
    """Runtime data for the Wattpilot integration."""

    charger: Any  # Wattpilot client instance
    push_entities: dict[str, ChargerPlatformEntity] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    debug_properties: bool = False
    options_update_listener: Any | None = None
    property_updates_callback: Any | None = None


type WattpilotConfigEntry = ConfigEntry[WattpilotRuntimeData]


class EntityConfig:
    """Type hints for entity configuration from YAML."""

    id: str
    name: str | None
    source: str  # "property" | "attribute" | "namespacelist"
    firmware: str | None
    variant: str | None
    connection: str | None
    icon: str | None
    device_class: str | None
    entity_category: str | None
    enabled: bool
    default_state: Any
    description: str | None
    enum: dict[Any, str] | None
    unit_of_measurement: str | None
    state_class: str | None
    set_type: str | None
    namespace_id: int
    value_id: str | None
    attribute_ids: list[str] | None
    invert: bool
    options: dict[Any, str] | list[str] | None
    native_min_value: float | None
    native_max_value: float | None
    native_step: float | None
    mode: str | None
    set_value: Any
    uid: str | None
    html_unescape: bool | None
