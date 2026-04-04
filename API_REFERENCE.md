# SpaNET API Reference

This document captures the endpoint contract currently implemented by this integration.

It is not a full upstream Swagger replacement. It is the repo's working reference for:

- endpoints used by the Home Assistant integration
- live-confirmed app request shapes
- cases where the app contract differed from the published Swagger behavior

The examples below use the observed live spa:

- `deviceId = 7138`
- `Pump A / circulation id = 12901`
- `Pump 1 id = 12902`
- `Pump 2 id = 12903`
- `Blower id = 6147`
- `Light id = 6156`

## Authentication

### Login

```http
POST /api/Login/Authenticate
```

Body:

```json
{
  "email": "user@example.com",
  "password": "secret",
  "userDeviceId": "client-device-id",
  "language": "en_AU"
}
```

### Device discovery

```http
GET /api/Devices
```

Used to discover available spas and their `id`, `name`, and `macAddress`.

## Dashboard and information

### Dashboard

```http
GET /api/Dashboard/{deviceId}
```

Primary live-state source for:

- set temperature
- current temperature
- heater
- sleeping
- sanitise active
- status list

Observed sanitise-active example:

```json
{
  "statusList": [
    "W.CLN",
    "Heating",
    "Sanitise Cycle: 19:48"
  ],
  "sanitiseOn": true,
  "statusFlags": {
    "SanitiseOn": true,
    "HeaterOn": true
  }
}
```

### Information

```http
GET /api/Information/{deviceId}
```

Currently used mainly for Element Boost support/state summary.

## Pumps and blower

### Read pumps and blower

```http
GET /api/PumpsAndBlower/Get/{deviceId}
```

Primary source for:

- pump capability
- pump state
- blower state
- blower variable speed

Observed blower readback semantics:

- `off` -> `blowerStatus = "off"`
- `ramp` -> `blowerStatus = "ramp"`
- `variable` -> `blowerStatus = "vari"`
- `blowerVariableSpeed` retains the last variable speed even when the blower is `off` or `ramp`

### Pump A

```http
PUT /api/PumpsAndBlower/SetPump/12901
```

App-confirmed contract:

- `off`

```json
{
  "modeId": 2,
  "deviceId": "7138",
  "pumpVariableSpeed": 0
}
```

- `auto`

```json
{
  "modeId": 3,
  "deviceId": "7138",
  "pumpVariableSpeed": 0
}
```

- `on`

```json
{
  "modeId": 1,
  "deviceId": "7138",
  "pumpVariableSpeed": 0
}
```

### Pump 1

```http
PUT /api/PumpsAndBlower/SetPump/12902
```

Observed app/user-confirmed contract:

- `off`

```json
{
  "modeId": 2,
  "deviceId": "7138",
  "pumpVariableSpeed": 0
}
```

- `on`

```json
{
  "modeId": 1,
  "deviceId": "7138",
  "pumpVariableSpeed": 0
}
```

Pump 1 is modeled as binary in Home Assistant even though some backend states can appear controller-driven.

### Pump 2

```http
PUT /api/PumpsAndBlower/SetPump/12903
```

Observed contract:

- `off`

```json
{
  "modeId": 2,
  "deviceId": "7138",
  "pumpVariableSpeed": 0
}
```

- `on`

```json
{
  "modeId": 1,
  "deviceId": "7138",
  "pumpVariableSpeed": 0
}
```

### Blower

```http
PUT /api/PumpsAndBlower/SetBlower/6147
```

App-confirmed write contract:

- `off`

```json
{
  "modeId": 1,
  "deviceId": "7138",
  "speed": 0
}
```

- `ramp`

```json
{
  "modeId": 3,
  "deviceId": "7138",
  "speed": 0
}
```

- `variable` speed `1..5`

```json
{
  "modeId": 2,
  "deviceId": "7138",
  "speed": 3
}
```

## Lights

### Read light details

```http
GET /api/Lights/GetLightDetails/{deviceId}
```

### Light on/off

```http
PUT /api/Lights/SetLightStatus/{lightId}
```

Body:

```json
{
  "deviceId": 7138,
  "on": true
}
```

### Light mode

```http
PUT /api/Lights/SetLightMode/{lightId}
```

Observed app mode strings:

- `colour`
- `fade`
- `step`
- `party`

### Light colour

```http
PUT /api/Lights/SetLightColour/{lightId}
```

Observed app colour values so far:

- `white`
- `blue`
- `green`
- `lime`
- `teal`
- `pink`
- `red`
- `orange`

Example:

```json
{
  "deviceId": "7138",
  "colour": "pink"
}
```

### Light brightness

```http
PUT /api/Lights/SetLightBrightness/{lightId}
```

Observed scale:

- `1..5`

### Light speed

```http
PUT /api/Lights/SetLightSpeed/{lightId}
```

Observed scale:

- `1..5`

Observed live readback example:

```json
{
  "lightMode": "party",
  "lightColour": "pink",
  "lightBrightness": 1,
  "lightSpeed": 1,
  "lightOn": true
}
```

## Settings

### Operation mode

```http
GET /api/Settings/OperationMode/{deviceId}
```

Observed response:

```json
2
```

Observed mapping:

- `1` -> `Normal`
- `2` -> `Economy`
- `3` -> `Away`
- `4` -> `Weekend`

### Power save

```http
GET /api/Settings/PowerSave/{deviceId}
PUT /api/Settings/PowerSave/{deviceId}
```

Observed read example:

```json
{
  "mode": 3,
  "startTime": "00:00:00",
  "endTime": "00:00:00"
}
```

Observed mapping:

- `1` -> `Off`
- `2` -> `Low`
- `3` -> `High`

### Heat pump

```http
GET /api/Settings/HeatPumpMode/{deviceId}
PUT /api/Settings/SetHeatPumpMode/{deviceId}
```

Observed read example:

```json
{
  "mode": 2,
  "svElementBoost": false
}
```

Observed mapping on the SV3 backend:

- `2` -> `Heat`
- `3` -> `Cool`
- `4` -> `Off`

The cloud API did not preserve `Auto` as a distinct mode on the observed spa, so the integration exposes `Heat / Cool / Off`.

### Element Boost

```http
PUT /api/Settings/SetElementBoost/{deviceId}
```

Body:

```json
{
  "svElementBoost": true
}
```

### Filtration

```http
GET /api/Settings/Filtration/{deviceId}
PUT /api/Settings/Filtration/{deviceId}
```

Observed read example:

```json
{
  "totalRuntime": 4,
  "inBetweenCycles": 3
}
```

Integration mapping:

- `totalRuntime` -> `Filtration Runtime`
- `inBetweenCycles` -> `Filtration Cycle Gap`

### Timeout

```http
GET /api/Settings/Timeout/{deviceId}
PUT /api/Settings/Timeout/{deviceId}
```

### Sanitise start time

```http
GET /api/Settings/Sanitise/{deviceId}
PUT /api/Settings/Sanitise/{deviceId}
```

Observed read behavior:

- plain text response, for example:

```text
14:00:00
```

Observed write body:

```json
{
  "time": "14:00"
}
```

### Date and time

```http
GET /api/Settings/DateTime/{deviceId}
PUT /api/Settings/DateTime/{deviceId}
```

Observed read behavior:

- plain text response, for example:

```text
05/04/2026 08:57:00AM
```

Observed write body:

```json
{
  "dateTime": "05-04-2026 08:57"
}
```

The integration exposes this as:

- a `Sync Spa Clock` button that writes the current local system time
- a `set_spa_datetime` service for explicit manual setting
- a read-only `Spa Clock` sensor showing the controller's returned text value

### Sanitise start/stop action

```http
PUT /api/Settings/SanitiseStatus/{deviceId}
```

App-confirmed request bodies:

- start

```json
{
  "on": true
}
```

- stop

```json
{
  "on": false
}
```

Important:

- the app-shaped JSON body works
- the Swagger-style query-only form was misleading on the observed spa

## Sleep timers

### Read timers

```http
GET /api/SleepTimers/{deviceId}
```

Observed timer object shape:

```json
{
  "id": 12295,
  "timerNumber": 1,
  "timerName": "Timer 1",
  "startTime": "22:00",
  "endTime": "09:00",
  "daysHex": "7F",
  "isEnabled": true,
  "show": false,
  "allowHeating": false
}
```

### Partial timer update

```http
PUT /api/SleepTimers/{timerId}
```

Observed app contract uses partial payloads.

#### Enable/disable

```json
{
  "timerNumber": 1,
  "deviceId": "7138",
  "isEnabled": true
}
```

#### Start time

```json
{
  "timerNumber": 1,
  "startTime": "09:00 PM",
  "deviceId": "7138",
  "isEnabled": true
}
```

#### End time

```json
{
  "timerNumber": 1,
  "endTime": "09:00 AM",
  "deviceId": "7138",
  "isEnabled": true
}
```

#### Day profile

```json
{
  "timerNumber": 1,
  "daysHex": "7F",
  "deviceId": "7138",
  "isEnabled": true
}
```

### Timer create/delete

```http
POST /api/SleepTimers
DELETE /api/SleepTimers/{timerId}
```

These remain available through services in the integration.

## App settings summary

### Secondary summary endpoint

```http
GET /api/Settings/GetSettingsDetails?deviceId={deviceId}
```

Observed example:

```json
{
  "showRunTimers": false,
  "operationMode": "ECON",
  "heatPumpMode": "HEAT",
  "powersaveMode": "HIGH",
  "sanitiseTime": "14:00",
  "timeout": "20",
  "filtration": "4 | 3",
  "runTimers": "0",
  "sleepTimers": "2",
  "lockMode": "OFF",
  "supportMode": false
}
```

This endpoint is used as a secondary diagnostics/app-parity source only.
Dedicated endpoints remain the primary source of truth for writable settings.

## Known contract notes

- The app and published Swagger did not always match.
- The repo prefers the app-confirmed contract when live behavior contradicts Swagger.
- Current known cases:
  - sanitise start/stop uses JSON body, not query-only
  - blower off/ramp use `speed: 0`
  - Pump A `on` is `modeId 1`, not `modeId 4`
  - sleep timer writes work cleanly as partial updates
