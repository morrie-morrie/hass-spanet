# SpaNET for Home Assistant

Maintained fork of the original [`lloydw/hass-spanet`](https://github.com/lloydw/hass-spanet) integration.

This fork is published from [`morrie-morrie/hass-spanet`](https://github.com/morrie-morrie/hass-spanet) and keeps credit to the original author for the initial implementation.

<img src="https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.spanet.total" align="right">

Control a SpaNET spa from Home Assistant using the SpaNET cloud API.

[![Open your Home Assistant instance and open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=morrie-morrie&repository=hass-spanet&category=Integration)

## Features

- Climate control for spa set temperature
- Water temperature, heater, sanitise, and sleeping sensors
- Pump control driven by live spa capabilities
  - `Pump 1`: `off / auto / on` when auto mode is supported
  - binary fallback for pumps that only support `off / on`
- Blower control
  - `Blower Mode`: `off / ramp / variable`
  - `Blower Speed`: `1-5` when blower mode is `variable`
- Native light entity plus advanced light controls
  - on/off
  - brightness `1-5`
  - profile: `Single` or `Animated`
  - animation: `Fade`, `Step`, `Party`
  - animation speed `1-5`
- Settings entities for:
  - Operation Mode
  - Power Save
  - Heat Pump mode
  - Element Boost
  - Filtration Runtime
  - Filtration Cycle Gap
  - Timeout
  - Sanitise Time
  - Sleep Timers

## Configuration

Add the integration in Home Assistant and enter your SpaNET email address and password.

All spas on the account are discovered and added under the one config entry.

### Options

- `Enable Heat Pump`
  - Enables the Heat Pump mode entity
  - Enables the Element Boost switch
  - If disabled, Element Boost is not added

## Entity model

This fork prefers native Home Assistant entities where the API contract is clear and uses services for the more advanced or underdocumented actions.

### Pumps

- Pumps are created from the live `PumpsAndBlower/Get` response
- Auto-capable pumps are exposed as `select` entities
- Binary-only pumps are exposed as `switch` entities
- Duplicate pump entities are intentionally avoided

### Blower

- No blower switch is created
- Mode is handled with a `select`
- Speed is handled with a `number`

### Lights

- `Light` is exposed as a native HA `light` entity
- Advanced light controls are exposed as select/number entities and services

## Services

Domain: `spanet`

- `set_light_mode`
- `set_light_colour`
- `create_sleep_timer`
- `update_sleep_timer`
- `delete_sleep_timer`
- `set_sanitise_status`

## Notes

- This integration uses the SpaNET cloud API and is therefore `cloud_polling`
- Some controls depend on the capabilities reported by the spa and may vary between models
- Entity availability is intentionally driven by live API support where possible

## Repository

- Source: [morrie-morrie/hass-spanet](https://github.com/morrie-morrie/hass-spanet)
- Original project: [lloydw/hass-spanet](https://github.com/lloydw/hass-spanet)
- Issues: [morrie-morrie/hass-spanet/issues](https://github.com/morrie-morrie/hass-spanet/issues)

## Release flow

HACS shows commit hashes when the repository has no version tags or GitHub releases. This fork now includes a release workflow that publishes GitHub releases from semantic version tags.

### Automatic release from `main`

1. Update `custom_components/spanet/manifest.json` with the new version
2. Commit the change
3. Push to `main`
4. GitHub Actions creates the matching tag and GitHub release automatically

Example:

```powershell
git add custom_components/spanet/manifest.json README.md
git commit -m "Release 1.1.15"
git push origin main
```

The workflow derives the tag from `manifest.json`, for example version `1.1.15` becomes tag `v1.1.15`.

### Manual or tag-based release

You can also run the `Release` workflow manually in GitHub Actions and provide:

- `tag`: the release tag, for example `v1.1.15`
- `target`: the git ref to release from, default `main`

Or push a matching tag directly:

```powershell
git tag v1.1.15
git push origin v1.1.15
```

The workflow validates that the tag matches `manifest.json` and only creates the tag or release if it does not already exist.
