# AGENTS.md

## Purpose

This repository contains a Home Assistant custom integration for SpaNET.

Use this file as the local instruction set for future AI-assisted edits in this repo.

## Core expectations

- Prefer small, explicit changes over broad refactors
- Keep Home Assistant entity IDs and unique IDs stable unless a control is intentionally removed
- Add or update tests where practical
- Aim for Home Assistant Gold Standard quality wherever feasible, following official Home Assistant integration rules and best practices
- Keep `custom_components/spanet/quality_scale.yaml` updated when quality-scale relevant behavior changes
- Run validation after code changes:
  - `python -m compileall custom_components/spanet tests`
  - `python -m pytest -q`
- When documentation or behavior changes, update `README.md`
- When endpoint contracts are clarified, update `API_REFERENCE.md`
- When shipping a change intended for users, update `custom_components/spanet/manifest.json` version
- Prefer pinned Python requirements in `manifest.json`

## Home Assistant quality target

Future work in this repository should aim toward Home Assistant Gold Standard expectations, not just minimum functionality.

This means preferring:

- clear, user-facing behavior that matches Home Assistant conventions
- robust config flow and options flow behavior
- stable entities and service contracts
- diagnostics, translations, and documentation kept in sync
- strong test coverage for changed behavior
- avoiding UI clutter when a service or native HA pattern is a better fit
- tracking progress toward Platinum-level Home Assistant standards without claiming a tier the repo has not actually earned

When making design tradeoffs, prefer the option that better aligns with Home Assistant integration guidance unless there is a strong repo-specific reason not to.

When improving quality-scale alignment, prioritize real Home Assistant outcomes over badge-chasing:
- correct auth vs connectivity error handling
- `ConfigEntry.runtime_data` usage
- diagnostics and docs that stay aligned with real behavior
- reducing noisy or privacy-heavy logging
- replacing wildcard imports and ambiguous state access with explicit imports/types where practical

## Current product model

### Device-page entities

Keep the Home Assistant device page intentionally simple.

- Pumps are capability-driven:
  - `Pump A` is derived from the circulation pump and uses a select: `off / auto / on`
  - `Pump 1` is switch-based
  - `Pump 2` is switch-based
  - do not assume one shared pump mode mapping across all pumps; use live pump-role behavior
- Blower is exposed as:
  - `Blower Mode` select: `off / ramp / variable`
  - `Blower Variable Speed` numeric control for `1-5`
  - the speed control is always visible for UX, but only meaningful when mode is `variable`
  - blower is modeled separately from the pump switches even if it alters swim-pump behavior on the spa
  - for the observed app contract, blower writes use `off = (modeId 1, speed 0)`, `ramp = (modeId 3, speed 0)`, `variable = (modeId 2, speed 1..5)`
- Lights are exposed through the native `light` entity
- Schedules and stable settings should prefer native HA entities
- Advanced behavior should prefer services over extra select/number entities where possible
- Light services should follow raw app mode/colour strings where the cloud API already uses them, for example `colour`, `fade`, `step`, `party`, and colours like `white`, `blue`, `green`, `lime`, `teal`, `pink`, `red`, and `orange`

### Advanced controls

Prefer service-based control for advanced or clutter-prone actions:

- blower mode and blower speed
- advanced light mode, colour, and light speed

If a new feature can be represented either as a device-page entity or a service, prefer:
- entity for common day-to-day control
- service for advanced, rare, or mode-like operations

## Important implementation rules

### Entity cleanup

This integration intentionally removes stale retired entities from the entity registry in `custom_components/spanet/__init__.py`.

If you remove or replace an entity type:
- add cleanup for the retired entity IDs/unique IDs
- avoid leaving old entities behind in Home Assistant

### Capability-driven behavior

Use live API capability/state data as the source of truth.

Examples:
- pumps come from `PumpsAndBlower/Get`
- the circulation pump may need to be modeled separately as `Pump A`
- for the observed SV3 app contract, `Pump A` uses `off = 2`, `auto = 3`, `on = 1`
- unsupported controls should not be forced into the UI
- when an option is config-gated, preserve that gate unless intentionally changing product behavior
- `Settings/GetSettingsDetails` is a secondary summary source for diagnostics/app parity, not the primary source of truth for writable settings
- Filtration mapping follows the dedicated endpoint contract:
  - `totalRuntime` -> `Filtration Runtime`
  - `inBetweenCycles` -> `Filtration Cycle Gap`

### Heat pump option

`Enable Heat Pump` in the config/options flow currently gates:
- the `Heat Pump` select entity
- the `Element Boost` switch

For the observed SV3 cloud backend:
- `Heat Pump` should use `Heat / Cool / Off`
- do not assume `Auto` is a stable distinct cloud mode unless revalidated on a real spa

Do not decouple these unless explicitly requested.

### Sanitise behavior

Sanitise is treated as an action-oriented behavior, not a true persistent switch.

- `Run Sanitise` is a button
- `Stop Sanitise` is a button
- `Sanitise Active` is a binary sensor sourced from live dashboard state
- `Sanitise Status` and `Sanitise Countdown` are read-only sensors derived from the dashboard `statusList`
- Do not expose sanitise as a toggleable switch
- The working live request shape is:
  - `PUT /api/Settings/SanitiseStatus/{deviceId}`
  - JSON body `{ "on": true }` to start
  - JSON body `{ "on": false }` to stop
- Do not fall back to the Swagger-style query-only form unless the app-shaped request stops working

### Sleep timer behavior

- Sleep timer `Days` should only present writable named profiles
- `Custom` should be surfaced as a derived/display state when the API returns a non-standard `daysHex`, not as a normal selectable preset
- Sleep timer entity writes should follow the app-shaped partial update contract on `/SleepTimers/{timerId}`
- Use partial payloads with `deviceId`, `timerNumber`, the changed field, and current `isEnabled`
- Use app-style time strings such as `09:00 PM` for timer start/end writes

### Lock Mode

`Lock Mode` has been removed from the UI due to poor fit and API behavior uncertainty.

Do not reintroduce it without a clear requirement and validated behavior.

## Key files

- `custom_components/spanet/__init__.py`
  - platform loading
  - stale entity cleanup
  - service registration lifecycle
- `custom_components/spanet/coordinator.py`
  - state model
  - write paths
  - capability parsing
- `custom_components/spanet/services.py`
  - advanced control services
- `custom_components/spanet/switch.py`
  - binary pumps, sleep timers, element boost
- `custom_components/spanet/select.py`
  - `Pump A`, blower mode, configuration selects
- `custom_components/spanet/number.py`
  - blower variable speed
- `custom_components/spanet/light.py`
  - native light entity
- `custom_components/spanet/binary_sensor.py`
  - cloud connected, heater, sanitise active, sleeping, and pump run-state sensors
- `custom_components/spanet/sensor.py`
  - temperature sensors
- `custom_components/spanet/api_mappings.py`
  - centralized state/mode mappings

## Release flow

This repo uses an automated GitHub Actions release flow.

- Version lives in `custom_components/spanet/manifest.json`
- Pushes to `main` create matching tags/releases automatically
- Keep README release examples in sync with the current version when editing release docs

## Documentation expectations

If services change:
- update `custom_components/spanet/services.yaml`
- update `custom_components/spanet/strings.json`
- update `custom_components/spanet/translations/en.json`
- update the README service section with practical examples

If entity behavior changes:
- update the README feature/entity-model sections

## Testing guidance

Prefer focused regression tests for:

- coordinator write behavior
- entity setup and visibility
- stale entity cleanup behavior when practical
- API payload contract changes

Existing tests rely on lightweight Home Assistant stubs. Extend those rather than introducing unnecessary complexity.
