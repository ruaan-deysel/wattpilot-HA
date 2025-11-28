# Wattpilot-HA Copilot Instructions

## Project Overview
Custom Home Assistant integration for [Fronius Wattpilot](https://www.fronius.com/en/solar-energy/installers-partners/technical-data/all-products/solutions/fronius-wattpilot) EV charging devices. Uses an embedded wattpilot Python library (reverse-engineered WebSocket API) at `custom_components/wattpilot/wattpilot/`.

**Version**: 0.3.7 | **HA**: ≥2024.4.0 | **Python**: 3.13+ | **HACS**: ≥1.34.0

## Development Workflow

### Dev Container Setup
```bash
# 1. Initial setup (install dependencies)
scripts/setup

# 2. Start Home Assistant instance for debugging
scripts/develop    # Starts HA at http://localhost:8123

# 3. Lint and format code
scripts/lint       # Runs ruff format + ruff check --fix
```

The dev container mounts `custom_components/` to HA's PYTHONPATH. Config stored in `config/`.

### Debugging
- **HA Logs**: Check `config/home-assistant.log` or use Developer Tools → Logs in UI
- **Debug mode**: `scripts/develop` runs with `--debug` flag for verbose logging
- **Integration logs**: Add to `config/configuration.yaml`:
  ```yaml
  logger:
    default: warning
    logs:
      custom_components.wattpilot: debug
  ```
- **Live reload**: Restart HA from Developer Tools → YAML → Restart after code changes

### Code Quality
- **Linter**: Ruff with ALL rules enabled (see `.ruff.toml`)
- **Target**: Python 3.13
- **Format**: Run `scripts/lint` before committing
- **Zero tolerance**: All linting warnings and errors MUST be fixed before committing - no exceptions

## Architecture

### Core Components
| File | Responsibility |
|------|----------------|
| `__init__.py` | Entry point: charger connection, platform setup, service & callback registration |
| `entities.py` | Base `ChargerPlatformEntity` with firmware/variant/connection validation |
| `utils.py` | Property get/set helpers, dynamic wattpilot module loading |
| `config_flow.py` | UI configuration wizard (local IP or cloud connection) |
| `{platform}.py` | Platform implementations reading from `{platform}.yaml` |

### YAML-Driven Entity Configuration
Entities defined declaratively in `{platform}.yaml`. Schema:
```yaml
- source: property | attribute | namespacelist
  id: <api_key>                    # From go-eCharger API v2
  name: "Display Name"
  firmware: ">=38.5"               # Firmware version constraint
  variant: "11" | "22"             # 11kW or 22kW variant only
  connection: "local" | "cloud"    # Connection type constraint
  enum: {0: "Off", 1: "On"}        # State mapping
  enabled: false                   # Disable by default
  entity_category: config          # HA entity category
```

### Data Flow
```
WebSocket → charger.allProps → PropertyUpdateHandler → push_entities → HA state
```
- Push entities (property source) get real-time updates via `async_local_push()`
- Poll entities (attribute/namespacelist) update via `async_local_poll()`

## API Reference
Property keys from [go-eCharger API v2](https://github.com/goecharger/go-eCharger-API-v2/blob/main/apikeys-en.md):
- `car`: carState (Idle=1, Charging=2, WaitCar=3, Complete=4)
- `amp`: requestedCurrent in Ampere
- `frc`: forceState (Neutral=0, Off=1, On=2)
- `lmo`: logic mode (Default=3, Eco=4, NextTrip=5)
- `nrg`: energy array [U_L1-3, I_L1-3, P_L1-3, pf_L1-3]
- `eto`: energy_total in Wh
- `wh`: energy since car connected in Wh

## Key Patterns

### Property Access
```python
from .utils import async_GetChargerProp, async_SetChargerProp, GetChargerProp

# Async read/write
value = await async_GetChargerProp(charger, 'amp', default=6)
await async_SetChargerProp(charger, 'amp', 16)

# Sync read (use in properties)
value = GetChargerProp(charger, 'amp', default=6)
```

### Adding New Entities
1. Find property key in go-eCharger API docs
2. Add YAML entry to `{platform}.yaml`
3. Entity auto-created from `ChargerPlatformEntity` subclass
4. For property source, entity auto-registered for push updates

### Service Implementation
```python
# services.yaml defines schema, services.py implements
await async_registerService(hass, "service_name", async_service_handler)
```

## Conventions
- **Logging**: `_LOGGER.debug("%s - %s: message", entry_id, method_name)`
- **Data storage**: `hass.data[DOMAIN][entry.entry_id][CONF_CHARGER]`
- **Unique IDs**: `{charger_friendly_name}-{entity_uid}`
- **Push entities**: Registered in `CONF_PUSH_ENTITIES` dict

## Embedded wattpilot Library
Located at `custom_components/wattpilot/wattpilot/src/wattpilot/`. Key exports:
- `Wattpilot`: Main client class with `allProps` dict, `connected` state
- `Event.WP_PROPERTY`: Callback event for property changes
- `LoadMode`: Enum (DEFAULT=3, ECO=4, NEXTTRIP=5)

The `utils.py` dynamically loads local copy, falling back to pip-installed version.

## Dependencies
From `manifest.json`: `wattpilot>=0.2`, `pyyaml>=5.3.0`, `aiofiles>=23.2.1`, `packaging>=24.0`

## Testing

### Structure (To Be Implemented)
```
tests/
├── conftest.py              # Shared fixtures (mock charger, hass instance)
├── test_init.py             # Config entry setup/unload tests
├── test_config_flow.py      # Config flow UI tests
├── test_sensor.py           # Sensor entity tests
├── test_switch.py           # Switch entity tests
├── test_services.py         # Service call tests
└── fixtures/
    └── charger_data.json    # Mock charger property responses
```

### Testing Patterns for HA Integrations
- Use `pytest-homeassistant-custom-component` for HA test fixtures
- Mock `Wattpilot` WebSocket client in `conftest.py`
- Test entity creation from YAML configs
- Verify push/poll update mechanisms
- Test firmware/variant/connection filtering logic

## Modernization Opportunities

The codebase has areas that could be updated to follow current Python/HA best practices:

### Python Style
- **Boolean comparisons**: Replace `if x == True:` → `if x:` and `if x == False:` → `if not x:`
- **None comparisons**: Replace `if x is None` checks where `if not x` suffices
- **Exception handling**: Replace broad `except Exception as e:` with specific exceptions
- **Type hints**: Add return type annotations to methods (currently inconsistent)
- **f-strings**: Some string formatting could use f-strings

### Home Assistant Patterns
- **ConfigEntry data**: Consider using `entry.runtime_data` (HA 2024.x+) instead of `hass.data[DOMAIN]`
- **Entity descriptions**: Migrate to `EntityDescription` dataclasses instead of YAML dicts
- **Async context managers**: Use `async with` for resource management
- **Coordinator pattern**: Consider `DataUpdateCoordinator` for poll entities

### Code Examples to Modernize
```python
# Before
if self._init_failed == True:
    return False
if not self._entity_category is None:
    return EntityCategory(self._entity_category)

# After  
if self._init_failed:
    return False
if self._entity_category is not None:
    return EntityCategory(self._entity_category)
```

## Releases & Versioning

### Version Locations
Update version in these files when releasing:
- `custom_components/wattpilot/manifest.json` → `"version": "x.y.z"`
- `hacs.json` → update if HA/HACS minimum versions change

### HACS Release Process
1. Update version numbers
2. Update `CHANGELOG.md` with changes (REQUIRED for every release)
3. Run `scripts/lint` to ensure code quality (must have zero warnings/errors)
4. Commit and push to `master`
5. Create GitHub release with tag `vX.Y.Z`
6. HACS automatically picks up new releases from GitHub tags

### Changelog
- **CHANGELOG.md** MUST be kept up to date with all changes
- Follow [Keep a Changelog](https://keepachangelog.com/) format
- Group changes under: Added, Changed, Deprecated, Removed, Fixed, Security

### Versioning Convention
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Current: `0.3.7` (pre-1.0, breaking changes possible in minor versions)
