# SpaNET for Home Assistant

Maintained fork of the original [`lloydw/hass-spanet`](https://github.com/lloydw/hass-spanet) integration.

This fork is published from [`morrie-morrie/hass-spanet`](https://github.com/morrie-morrie/hass-spanet) and keeps credit to the original author for the initial implementation.

<img src="https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.spanet.total" align="right">

Control a SpaNET spa from Home Assistant using the SpaNET cloud API.

[![Open your Home Assistant instance and open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=morrie-morrie&repository=hass-spanet&category=Integration)

## Features

- Climate control for spa set temperature
- Water temperature, heater, sanitise, and sleeping sensors
- Pump control as simple switch entities on the device page
  - `Pump 1`
  - `Pump 2`
- Blower control as a simple switch entity on the device page
- Native light entity for everyday light control
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
- Pumps are exposed as `switch` entities on the device page
- Advanced pump mode changes such as `auto` are exposed via services
- Duplicate pump entities are intentionally avoided and stale retired pump entities are cleaned up on setup

### Blower

- `Blower` is exposed as a `switch` on the device page
- Turning the blower on uses the integration's default active blower mode
- Advanced blower mode and speed control are exposed via services

### Lights

- `Light` is exposed as a native HA `light` entity
- Advanced light mode, colour, and speed control are exposed via services

## Services

Domain: `spanet`

- `set_light_mode`
- `set_light_colour`
- `set_light_speed`
- `set_pump_mode`
- `set_blower_mode`
- `set_blower_speed`
- `create_sleep_timer`
- `update_sleep_timer`
- `delete_sleep_timer`
- `set_sanitise_status`

These services are intended for automations, scripts, dashboard buttons, and manual calls from Developer Tools.

### Why services exist

The device page is kept intentionally simple:

- pumps are switches
- blower is a switch
- light is a native light entity

Advanced actions that would otherwise clutter the device page are exposed as services instead.

### Common service examples

Pump 1 to auto mode:

```yaml
service: spanet.set_pump_mode
data:
  spa_id: "12345"
  pump: 1
  mode: auto
```

Blower to ramp mode:

```yaml
service: spanet.set_blower_mode
data:
  spa_id: "12345"
  mode: ramp
```

Blower speed to 5:

```yaml
service: spanet.set_blower_speed
data:
  spa_id: "12345"
  speed: 5
```

Set light animation mode:

```yaml
service: spanet.set_light_mode
data:
  spa_id: "12345"
  mode: Party
```

Set light colour:

```yaml
service: spanet.set_light_colour
data:
  spa_id: "12345"
  colour: blue
```

Set animated light speed:

```yaml
service: spanet.set_light_speed
data:
  spa_id: "12345"
  speed: 3
```

Trigger sanitise:

```yaml
service: spanet.set_sanitise_status
data:
  spa_id: "12345"
  on: true
```

### Service reference

`set_pump_mode`
- Use for advanced pump modes such as `auto`
- Fields:
  - `spa_id`
  - `pump`
  - `mode`: `off`, `on`, `auto`

`set_blower_mode`
- Use for `off`, `ramp`, or `variable`
- Fields:
  - `spa_id`
  - `mode`

`set_blower_speed`
- Sets blower variable speed `1-5`
- Fields:
  - `spa_id`
  - `speed`

`set_light_mode`
- Sets a raw SpaNET light mode string such as `Single`, `Fade`, `Step`, or `Party`
- Fields:
  - `spa_id`
  - `mode`

`set_light_colour`
- Sets a raw SpaNET light colour string
- Fields:
  - `spa_id`
  - `colour`

`set_light_speed`
- Sets animated light speed `1-5`
- Fields:
  - `spa_id`
  - `speed`

`set_sanitise_status`
- Triggers sanitise when `on: true`
- `on: false` is accepted for compatibility but ignored
- Fields:
  - `spa_id`
  - `on`

`create_sleep_timer`
- Creates a sleep timer profile

`update_sleep_timer`
- Updates an existing sleep timer profile

`delete_sleep_timer`
- Deletes an existing sleep timer profile

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
git commit -m "Release 1.1.20"
git push origin main
```

The workflow derives the tag from `manifest.json`, for example version `1.1.20` becomes tag `v1.1.20`.

### Manual or tag-based release

You can also run the `Release` workflow manually in GitHub Actions and provide:

- `tag`: the release tag, for example `v1.1.15`
- `tag`: the release tag, for example `v1.1.20`
- `target`: the git ref to release from, default `main`

Or push a matching tag directly:

```powershell
git tag v1.1.20
git push origin v1.1.20
```

The workflow validates that the tag matches `manifest.json` and only creates the tag or release if it does not already exist.
