"""Centralized API contract mappings for SpaNET."""

from __future__ import annotations

from typing import Any
import re

OPERATION_MODE_LABELS_BY_API = {
    1: "Normal",
    2: "Economy",
    3: "Away",
    4: "Weekend",
}
OPERATION_MODE_API_BY_LABEL = {label: api for api, label in OPERATION_MODE_LABELS_BY_API.items()}
OPERATION_MODE_OPTIONS = list(OPERATION_MODE_API_BY_LABEL)

POWER_SAVE_LABELS_BY_API = {
    1: "Off",
    2: "Low",
    3: "High",
}
POWER_SAVE_API_BY_LABEL = {label: api for api, label in POWER_SAVE_LABELS_BY_API.items()}
POWER_SAVE_OPTIONS = list(POWER_SAVE_API_BY_LABEL)

HEAT_PUMP_LABELS_BY_API = {
    1: "Auto",
    2: "Heat",
    3: "Cool",
    4: "Off",
}
HEAT_PUMP_API_BY_LABEL = {label: api for api, label in HEAT_PUMP_LABELS_BY_API.items()}
HEAT_PUMP_OPTIONS = list(HEAT_PUMP_API_BY_LABEL)

LOCK_MODE_LABELS_BY_API = {
    0: "off",
    1: "on",
}

PUMP_STATE_TO_API = {
    "on": {"modeId": 4, "pumpVariableSpeed": 0},
    "off": {"modeId": 2, "pumpVariableSpeed": 0},
    "auto": {"modeId": 3, "pumpVariableSpeed": 0},
}

STANDARD_PUMP_STATE_TO_API = {
    "on": {"modeId": 1, "pumpVariableSpeed": 0},
    "off": {"modeId": 2, "pumpVariableSpeed": 0},
    "auto": {"modeId": 3, "pumpVariableSpeed": 0},
}

PUMP_ONE_STATE_TO_API = {
    "on": {"modeId": 3, "pumpVariableSpeed": 0},
    "off": {"modeId": 2, "pumpVariableSpeed": 0},
}

CIRCULATION_PUMP_STATE_TO_API = {
    "on": {"modeId": 4, "pumpVariableSpeed": 0},
    "off": {"modeId": 2, "pumpVariableSpeed": 0},
    "auto": {"modeId": 3, "pumpVariableSpeed": 0},
}

BLOWER_STATE_TO_API = {
    "off": {"modeId": 1},
    "ramp": {"modeId": 3},
    "variable": {"modeId": 2},
}

LIGHT_ANIMATION_OPTIONS = ["Fade", "Step", "Party"]
PUMP_SELECT_OPTIONS = ["off", "auto", "on"]


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def operation_mode_from_api(value: Any) -> str:
    api_value = _coerce_int(value)
    if api_value is None:
        return "Unknown"
    return OPERATION_MODE_LABELS_BY_API.get(api_value, "Unknown")


def power_save_from_api(value: Any) -> str:
    api_value = _coerce_int(value)
    if api_value is None:
        return "Unknown"
    return POWER_SAVE_LABELS_BY_API.get(api_value, "Unknown")


def heat_pump_from_api(value: Any) -> str:
    api_value = _coerce_int(value)
    if api_value is None:
        return "Off"
    return HEAT_PUMP_LABELS_BY_API.get(api_value, "Off")


def lock_mode_from_api(value: Any) -> str:
    api_value = _coerce_int(value)
    if api_value is None:
        return "off"
    return LOCK_MODE_LABELS_BY_API.get(api_value, "off")


def extract_time_string(value: Any) -> str | None:
    """Extract an HH:MM-style value from common SpaNET API payload shapes."""
    if value is None:
        return None

    if isinstance(value, dict):
        for key in ("time", "startTime", "endTime", "dateTime", "value"):
            nested = extract_time_string(value.get(key))
            if nested:
                return nested
        return None

    text = str(value).strip()
    if not text:
        return None

    if "T" in text:
        time_part = text.split("T", 1)[1]
        text = time_part.rstrip("Z")

    if " " in text:
        text = text.split(" ", 1)[0]

    match = re.search(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})", text)
    if match is None:
        return None

    try:
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
    except (TypeError, ValueError):
        return None

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    return f"{hour:02d}:{minute:02d}"


def normalize_light_mode(value: Any) -> str | None:
    """Normalize light mode labels from API payloads."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    for option in LIGHT_ANIMATION_OPTIONS:
        if lowered == option.lower():
            return option
    if lowered == "single":
        return "Single"
    return text
