# SpaNET for Home Assistant

Maintained fork of the original [`lloydw/hass-spanet`](https://github.com/lloydw/hass-spanet) integration.

This fork is published from [`morrie-morrie/hass-spanet`](https://github.com/morrie-morrie/hass-spanet) and keeps credit to the original author for the initial implementation.

<img src="https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.spanet.total" align="right">

Control a SpaNET spa from Home Assistant using the SpaNET cloud API.

[![Open your Home Assistant instance and open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=morrie-morrie&repository=hass-spanet&category=Integration)

Endpoint reference:
- [API_REFERENCE.md](C:\Scripts\C#\hass-spanet-morrie\API_REFERENCE.md)

## Features

- Climate control for spa set temperature
- Cloud connectivity binary sensor for SpaNET cloud reachability
- Water temperature and set temperature sensors
- `Pump A Mode` sensor for the current Pump A operating state
- Binary sensors for heater, sanitise active, sleeping, and pump run-state
- Capability-driven pump control from `PumpsAndBlower/Get`
  - `Pump A` is exposed as a `select`: `off / auto / on`
  - `Pump 1` is exposed as a `switch`
  - `Pump 2` is exposed as a `switch`
- Blower control as:
  - `Blower Mode` select: `off / ramp / variable`
  - `Blower Variable Speed` numeric control `1-5` when mode is `variable`
- Native light entity for everyday light control
- Settings entities for:
  - Operation Mode
  - Power Save
  - Heat Pump mode
  - Element Boost
  - Filtration Runtime
  - Filtration Cycle Gap
  - Timeout
  - Sanitise Start Time
  - Sleep Timers

## Configuration

Add the integration in Home Assistant and enter your SpaNET email address and password.

All spas on the account are discovered and added under the one config entry.

### Options

- `Enable Heat Pump`
  - Enables the Heat Pump mode entity
  - Enables the Element Boost switch
  - If disabled, Heat Pump and Element Boost are not added
  - On the observed SV3 backend, Heat Pump is exposed as `Heat / Cool / Off`; SpaNET does not preserve a distinct `Auto` mode through the cloud API

## Entity model

This fork prefers native Home Assistant entities where the API contract is clear and uses services for the more advanced or underdocumented actions.

### Pumps

- Pumps are created from the live `PumpsAndBlower/Get` response
- `Pump A` is derived from the circulation pump and is exposed as a `select` with `off / auto / on`
- `Pump 1` is exposed as a `switch`
- `Pump 2` is exposed as a `switch`
- Pump mappings are role-specific and based on live observed API behavior, not one shared pump-mode assumption
- `Pump A` follows the app-confirmed write contract: `off = modeId 2`, `auto = modeId 3`, `on = modeId 1`
- Duplicate pump entities are intentionally avoided and stale retired pump entities are cleaned up on setup

### Blower

- `Blower Mode` is exposed as a `select` with `off / ramp / variable`
- `Blower Variable Speed` is exposed as a numeric control `1-5`
- `Blower Variable Speed` is always visible so the control is easy to reach, but it is only meaningful when `Blower Mode` is `variable`
- The blower is modeled separately from the pump switches even if it changes the swim-pump characteristics on the spa
- The app-confirmed write contract is:
  - `off = modeId 1, speed 0`
  - `ramp = modeId 3, speed 0`
  - `variable = modeId 2, speed 1..5`
- Advanced blower control remains available through services for automations and scripts

### Lights

- `Light` is exposed as a native HA `light` entity
- Advanced light mode, colour, and speed control are exposed via services
- The app-confirmed light contract includes:
  - on/off via `PUT /api/Lights/SetLightStatus/{lightId}` with `{ "deviceId": "...", "on": true|false }`
  - mode strings such as `colour`, `fade`, `step`, and `party`
  - colour strings such as `white`, `blue`, `green`, `lime`, `teal`, `pink`, `red`, and `orange`
  - brightness and speed values on a `1..5` scale

### Sanitise

- `Sanitise Active` is exposed as a binary sensor from the live dashboard state
- `Sanitise Status` is exposed as a text sensor and reports values such as `W.CLN`
- `Sanitise Countdown` is exposed as a text sensor and reports values such as `19:48`
- `Run Sanitise` and `Stop Sanitise` are exposed as button actions
- `Sanitise Start Time` is exposed as a native `time` entity
- Sanitise is not modeled as a switch
- Live app capture showed the working trigger uses:
  - `PUT /api/Settings/SanitiseStatus/{deviceId}`
  - body: `{ "on": true }` to start
  - body: `{ "on": false }` to stop
- The Swagger-style query-string form was misleading; the integration now follows the app request shape

### Heat Pump / Element Boost

- `Heat Pump` is gated by `Enable Heat Pump`
- On the observed SV3 backend, the reliable cloud modes are:
  - `Heat`
  - `Cool`
  - `Off`
- `Element Boost` is a separate switch and was verified live to round-trip correctly

### Cloud/offline behavior

- `Cloud Connected` reports whether SpaNET cloud is returning live device data
- If SpaNET returns `Device Offline`, entities will become unavailable while the integration backs off polling
- That state indicates cloud/device reachability, not a broken integration install
- Filtration follows the dedicated REST contract:
  - `totalRuntime` -> `Filtration Runtime`
  - `inBetweenCycles` -> `Filtration Cycle Gap`
  - app summary strings such as `4 | 3` therefore mean `Runtime 4`, `Cycle Gap 3`

### App settings summary

- The integration also reads `GET /api/Settings/GetSettingsDetails?deviceId={deviceId}` as a secondary app-summary source
- This summary is used for diagnostics and app-parity checks only
- Dedicated endpoints remain the primary source of truth for writable settings and schedules

## Services

Domain: `spanet`

- `set_light_mode`
- `set_light_colour`
- `set_light_speed`
- `set_blower_mode`
- `set_blower_speed`
- `create_sleep_timer`
- `update_sleep_timer`
- `delete_sleep_timer`

These services are intended for automations, scripts, dashboard buttons, and manual calls from Developer Tools.

### Why services exist

The device page is kept intentionally simple for non-schedule advanced controls:

- pumps follow live capability
- blower mode is a select and variable speed is a dedicated numeric control
- light is a native light entity

Advanced light and blower actions that would otherwise clutter the device page are exposed as services instead.
Sleep timer CRUD services remain available because the API supports timer lifecycle operations beyond the fixed entity model.
The fixed timer entities map to timer slots `1` and `2`; `Custom` day profile is display-only when the API returns a non-standard `daysHex` value such as `FF`.
Sleep timer entity writes now follow the app-shaped partial update contract:
- timer enable writes send `timerNumber`, `deviceId`, and `isEnabled`
- timer time writes send the changed `startTime` or `endTime` in app-style `hh:mm AM/PM` format plus `isEnabled`
- timer day-profile writes send `daysHex` plus `isEnabled`

### Common service examples

Blower to ramp mode:

```yaml
service: spanet.set_blower_mode
data:
  spa_id: "12345"
  mode: ramp
```

Blower variable speed to 5:

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
  mode: party
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

Create Sleep Timer:

```yaml
service: spanet.create_sleep_timer
data:
  spa_id: "12345"
  timer_number: 2
  timer_name: "Timer 2"
  start_time: "22:00"
  end_time: "07:00"
  days_hex: "60"
  is_enabled: true
```

### Service reference

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
- Sets a raw SpaNET light mode string such as `colour`, `fade`, `step`, or `party`
- Fields:
  - `spa_id`
  - `mode`

`set_light_colour`
- Sets a raw SpaNET light colour string such as `white`, `blue`, `green`, `lime`, `teal`, `pink`, `red`, or `orange`
- Fields:
  - `spa_id`
  - `colour`

`set_light_speed`
- Sets animated light speed `1-5`
- Fields:
  - `spa_id`
  - `speed`

`create_sleep_timer`
- Creates a sleep timer profile using raw SpaNET timer fields

`update_sleep_timer`
- Updates an existing sleep timer profile using raw SpaNET timer fields

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
git commit -m "Release 1.2.14"
git push origin main
```

The workflow derives the tag from `manifest.json`, for example version `1.2.14` becomes tag `v1.2.14`.

### Manual or tag-based release

You can also run the `Release` workflow manually in GitHub Actions and provide:

- `tag`: the release tag, for example `v1.2.5`
  - current example: `v1.2.14`
- `target`: the git ref to release from, default `main`

Or push a matching tag directly:

```powershell
git tag v1.2.14
git push origin v1.2.14
```

The workflow validates that the tag matches `manifest.json` and only creates the tag or release if it does not already exist.
