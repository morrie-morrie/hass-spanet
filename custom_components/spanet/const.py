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

SL_HEATING = "Heating"
SL_SLEEPING = "Sleeping"
SL_SANITISE = "Sanitise"

OPERATION_MODES = ["Unknown", "Normal", "Economy", "Away", "Weekend"]
POWER_SAVE = ["Unknown", "Off", "Low", "High"]
HEAT_PUMP = ["Auto", "Heat", "Cool", "Off"]
SANITISER = ["Off", "On"]

OPT_ENABLE_HEAT_PUMP = "enable_heat_pump"
