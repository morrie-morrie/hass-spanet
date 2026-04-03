# AGENTS.md

## Purpose

This repository contains a Home Assistant custom integration for SpaNET.

Use this file as the local instruction set for future AI-assisted edits in this repo.

## Core expectations

- Prefer small, explicit changes over broad refactors
- Keep Home Assistant entity IDs and unique IDs stable unless a control is intentionally removed
- Add or update tests where practical
- Aim for Home Assistant Gold Standard quality wherever feasible, following official Home Assistant integration rules and best practices
- Run validation after code changes:
  - `python -m compileall custom_components/spanet tests`
  - `python -m pytest -q`
- When documentation or behavior changes, update `README.md`
- When shipping a change intended for users, update `custom_components/spanet/manifest.json` version

## Home Assistant quality target

Future work in this repository should aim toward Home Assistant Gold Standard expectations, not just minimum functionality.

This means preferring:

- clear, user-facing behavior that matches Home Assistant conventions
- robust config flow and options flow behavior
- stable entities and service contracts
- diagnostics, translations, and documentation kept in sync
- strong test coverage for changed behavior
- avoiding UI clutter when a service or native HA pattern is a better fit

When making design tradeoffs, prefer the option that better aligns with Home Assistant integration guidance unless there is a strong repo-specific reason not to.

## Current product model

### Device-page entities

Keep the Home Assistant device page intentionally simple.

- Pumps are exposed as switches
- Blower is exposed as a switch
- Lights are exposed primarily through the native `light` entity
- Advanced behavior should prefer services over extra select/number entities where possible

### Advanced controls

Prefer service-based control for advanced or clutter-prone actions:

- pump mode such as `auto`
- blower mode and blower speed
- advanced light mode, colour, and light speed
- sleep timer CRUD

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
- unsupported controls should not be forced into the UI
- when an option is config-gated, preserve that gate unless intentionally changing product behavior

### Heat pump option

`Enable Heat Pump` in the config/options flow currently gates:
- the `Heat Pump` select entity
- the `Element Boost` switch

Do not decouple these unless explicitly requested.

### Sanitise behavior

Sanitise is treated as an action-oriented behavior, not a true persistent switch.

- `Run Sanitise` is a button
- `set_sanitise_status` service exists for compatibility
- `on: false` requests are intentionally ignored

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
  - pumps, blower, sleep timers, element boost
- `custom_components/spanet/light.py`
  - native light entity
- `custom_components/spanet/sensor.py`
  - status sensors, including pump sensors
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
