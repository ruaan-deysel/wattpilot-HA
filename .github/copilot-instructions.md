# Wattpilot-HA Copilot Instructions

## Project Overview
Custom Home Assistant integration for [Fronius Wattpilot](https://www.fronius.com/en/solar-energy/installers-partners/technical-data/all-products/solutions/fronius-wattpilot) EV charging devices. Uses an embedded/vendored wattpilot Python library (based on reverse-engineered WebSocket API) located at `custom_components/wattpilot/wattpilot/`.

## Architecture

### Core Components
- **`__init__.py`**: Entry point - handles charger connection, platform setup, service registration, and property update callbacks
- **`entities.py`**: Base `ChargerPlatformEntity` class with firmware/variant/connection validation logic
- **`utils.py`**: Charger connection helpers, property get/set functions, dynamic module loading for embedded wattpilot library
- **Platform files** (`sensor.py`, `switch.py`, `select.py`, `number.py`, `button.py`, `update.py`): Each platform reads entity definitions from corresponding `.yaml` file

### YAML-Driven Entity Configuration
Entities are defined declaratively in `{platform}.yaml` files (e.g., `sensor.yaml`, `switch.yaml`). Key configuration options:
```yaml
- source: property | attribute | namespacelist  # Data source type
  id: <charger_property_name>                    # Maps to charger.allProps[id]
  firmware: ">=38.5"                             # Conditional: only create if firmware matches
  variant: "11" | "22"                           # Conditional: 11kW or 22kW variant
  connection: "local" | "cloud"                  # Conditional: connection type
  enum: {0: "Off", 1: "On"}                      # State value mapping
```

### Data Flow
1. Charger connects via WebSocket (local IP or cloud API)
2. Properties stored in `charger.allProps` dictionary
3. `PropertyUpdateHandler` in `utils.py` routes updates to push entities
4. Entities read current state from `charger.allProps[identifier]`

### Embedded wattpilot Library
Located at `custom_components/wattpilot/wattpilot/src/wattpilot/`. The `utils.py` dynamically loads this local copy, falling back to system-installed version. Key classes:
- `Wattpilot`: Main WebSocket client with `allProps`, connection management
- `Event.WP_PROPERTY`: Event type for property change callbacks

## Development Patterns

### Adding New Entities
1. Add entry to appropriate `{platform}.yaml` file
2. Entity class automatically created from `ChargerPlatformEntity` subclass
3. Use `id` matching charger property key from [go-eCharger API v2](https://github.com/goecharger/go-eCharger-API-v2/blob/main/apikeys-de.md)

### Property Access
```python
# Async read
value = await async_GetChargerProp(charger, 'property_id', default_value)
# Sync read  
value = GetChargerProp(charger, 'property_id', default_value)
# Async write
await async_SetChargerProp(charger, 'property_id', value)
```

### Service Registration
Services defined in `services.yaml`, implemented in `services.py` using `async_registerService()` helper.

## Key Conventions
- Use `_LOGGER.debug/warning/error` with format: `"%s - %s: message", entry_id, method_name`
- Config entry data stored in `hass.data[DOMAIN][entry.entry_id]`
- Push entities tracked in `CONF_PUSH_ENTITIES` dict for real-time updates
- Entity unique IDs format: `{charger_friendly_name}-{entity_uid}`

## Requirements
- Home Assistant ≥2024.4.0, HACS ≥1.34.0
- Dependencies: `wattpilot>=0.2`, `pyyaml`, `aiofiles`, `packaging`
