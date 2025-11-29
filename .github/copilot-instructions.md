# Wattpilot-HA Copilot Instructions

Custom Home Assistant integration for Fronius Wattpilot EV chargers using a reverse-engineered WebSocket API.

## Quick Start
```bash
scripts/setup      # Install dependencies (first time)
scripts/develop    # Start HA at http://localhost:8123 with debug logging
scripts/lint       # Format and lint (ruff format + check --fix) - REQUIRED before commits
```
Config in `config/`. Debug logging already enabled in `config/configuration.yaml`.

## Architecture Overview

**Data Flow**: `WebSocket → charger.allProps → PropertyUpdateHandler → push_entities → HA state`

| Component | Purpose |
|-----------|---------|
| `__init__.py` | Entry point: connects charger, registers services/callbacks, forwards to platforms |
| `entities.py` | Base `ChargerPlatformEntity` with firmware/variant/connection validation |
| `{platform}.py` + `{platform}.yaml` | Platform entities defined declaratively in YAML |
| `utils.py` | Property helpers, dynamic wattpilot module loading |
| `wattpilot/` | Embedded WebSocket library (local copy preferred over pip) |

## Embedded wattpilot Library

Located at `custom_components/wattpilot/wattpilot/src/wattpilot/`. The `utils.py` dynamically loads the local copy, falling back to pip-installed version:

```python
# utils.py loading logic (simplified)
base_path = os.path.dirname(__file__)  # custom_components/wattpilot/
local_module_path = os.path.join(base_path, 'wattpilot', 'src')
local_init_path = os.path.join(local_module_path, 'wattpilot', '__init__.py')
if os.path.exists(local_init_path):
    sys.path.insert(0, local_module_path)  # Prioritize local copy
import wattpilot
```

**Key exports from `wattpilot/__init__.py`:**
- `Wattpilot`: Main client class with WebSocket connection
  - `allProps`: Dict of all charger properties (source of truth)
  - `allPropsInitialized`: True when all properties loaded
  - `connected`: Connection state
  - `serial`, `name`, `firmware`: Device identifiers
- `Event.WP_PROPERTY`: Callback event for property changes
- `LoadMode`: Charging mode enum (DEFAULT=3, ECO=4, NEXTTRIP=5)
- Value mappings: `carValues`, `lmoValues`, `astValues`, `errValues`

## YAML-Driven Entities

Entities are configured in `{platform}.yaml`, not code. Schema:
```yaml
- source: property | attribute | namespacelist  # property = push, others = poll
  id: amp                          # go-eCharger API key
  name: "Requested Current"
  firmware: ">=38.5"               # Version constraint
  variant: "11" | "22"             # 11kW or 22kW only
  connection: "local" | "cloud"    # Connection type filter
  enum: {0: "Off", 1: "On"}        # State mapping
```

**Adding entities**: Find API key in [go-eCharger API v2](https://github.com/goecharger/go-eCharger-API-v2/blob/main/apikeys-en.md), add YAML entry. Entity auto-created.

## Key Patterns

```python
# Property access (utils.py)
from .utils import async_GetChargerProp, async_SetChargerProp, GetChargerProp

value = await async_GetChargerProp(charger, 'amp', default=6)  # async
await async_SetChargerProp(charger, 'amp', 16)                  # async write
value = GetChargerProp(charger, 'amp', default=6)               # sync (properties only)

# Data storage pattern
charger = hass.data[DOMAIN][entry.entry_id][CONF_CHARGER]
push_entities = hass.data[DOMAIN][entry.entry_id][CONF_PUSH_ENTITIES]

# Logging convention
_LOGGER.debug("%s - %s: message", entry_id, method_name)
```

## Services Pattern

Services defined in `services.yaml` (schema) + `services.py` (implementation):

```python
# Registration in __init__.py
await async_registerService(hass, "set_next_trip", async_service_SetNextTrip)

# Service implementation pattern (services.py)
async def async_service_SetNextTrip(hass: HomeAssistant, call: ServiceCall) -> None:
    device_id = call.data.get(CONF_DEVICE_ID, None)
    if device_id is None:
        _LOGGER.error("%s - async_service_SetNextTrip: %s is required", DOMAIN, CONF_DEVICE_ID)
        return None
    
    charger = await async_GetChargerFromDeviceID(hass, device_id)
    await async_SetChargerProp(charger, 'ftt', timestamp)
```

## Common API Keys
- `car`: carState (1=Idle, 2=Charging, 3=WaitCar, 4=Complete)
- `amp`: requestedCurrent (Ampere)
- `frc`: forceState (0=Neutral, 1=Off, 2=On)
- `lmo`: logic mode (3=Default, 4=Eco, 5=NextTrip)
- `nrg`: energy array, `eto`: total energy (Wh), `wh`: session energy (Wh)

## Code Quality
- **Linter**: Ruff with ALL rules (`.ruff.toml`), Python 3.13 target
- **Zero tolerance**: Fix ALL warnings before committing

**Known style debt** (fix when touching code):
```python
# Replace:  if x == True / if x == False / if not x is None
# With:     if x / if not x / if x is not None
```

## Releases
1. Update version in `custom_components/wattpilot/manifest.json`
2. Update `CHANGELOG.md` (required)
3. Run `scripts/lint`
4. Create GitHub release with tag `vX.Y.Z`
