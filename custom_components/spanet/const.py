"""Constants for the spanet integration."""

DOMAIN = "spanet"
DEVICE_ID = "device_id"

SK_SETTEMP = "setTemperature"
SK_WATERTEMP = "currentTemperature"
SK_HEATER = "heat"
SK_SANITISE = "sanitise"
SK_SLEEPING = "sleep"
SK_PUMPS = "pumps"
SK_OPERATION_MODE = "operationMode"
SK_POWER_SAVE = "powerSave"
SK_HEAT_PUMP = "heatPump"
SK_ELEMENT_BOOST = "elementBoost"
SK_ELEMENT_BOOST_SUPPORTED = "elementBoostSupported"
SK_SLEEP_TIMERS = "sleepTimers"
SK_LIGHTS = "lights"
SK_LIGHT_PROFILE = "lightProfile"
SK_LIGHT_ANIMATION = "lightAnimation"
SK_BLOWER = "blower"
SK_CLOUD_CONNECTED = "cloudConnected"
SK_FILTRATION_RUNTIME = "filtrationRuntime"
SK_FILTRATION_CYCLE = "filtrationCycle"
SK_TIMEOUT = "timeout"
SK_SANITISE_TIME = "sanitiseTime"

SL_HEATING = "Heating"
SL_SLEEPING = "Sleeping"

OPT_ENABLE_HEAT_PUMP = "enable_heat_pump"

ACCOUNT_UNIQUE_ID_PREFIX = "spanet-account:"

RETIRED_ENTITY_UNIQUE_IDS = set()

RETIRED_ENTITY_NAMES_BY_DOMAIN = {
    "datetime": {"DateTime", "Date/Time"},
    "sensor": {"Support Mode"},
    "switch": {"Sanitise Status", "Lock Mode", "Blower"},
    "time": {"Sanitise Time"},
    "binary_sensor": {"Sanitise"},
    "number": {
        "Light Brightness",
        "Light Speed",
        "Filtration Runtime",
        "Filtration Cycle Gap",
        "Timeout",
    },
    "select": {
        "Light Profile",
        "Light Animation",
    },
}

SLEEP_TIMER_DAY_PROFILES = {
    "Every Day": "7F",
    "Week Days": "1F",
    "Weekends": "60",
}
