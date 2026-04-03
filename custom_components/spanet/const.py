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
SK_FILTRATION_RUNTIME = "filtrationRuntime"
SK_FILTRATION_CYCLE = "filtrationCycle"
SK_LOCK_MODE = "lockMode"
SK_TIMEOUT = "timeout"
SK_SANITISE_TIME = "sanitiseTime"
SK_SANITISE_STATUS = "sanitiseStatus"
SK_DATE_TIME = "dateTime"
SK_SUPPORT_MODE = "supportMode"

SL_HEATING = "Heating"
SL_SLEEPING = "Sleeping"
SL_SANITISE = "Sanitise"

OPERATION_MODES = ["Unknown", "Normal", "Economy", "Away", "Weekend"]
POWER_SAVE = ["Unknown", "Off", "Low", "High"]
HEAT_PUMP = ["Auto", "Heat", "Cool", "Off"]
SANITISER = ["Off", "On"]

OPT_ENABLE_HEAT_PUMP = "enable_heat_pump"

SLEEP_TIMER_DAY_PROFILES = {
    "Every Day": "7F",
    "Week Days": "1F",
    "Weekends": "60",
}
