import logging
from datetime import timedelta

import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_mappings import (
    LIGHT_ANIMATION_OPTIONS,
    OPERATION_MODE_OPTIONS,
    PUMP_SELECT_OPTIONS,
    extract_time_string,
    heat_pump_from_api,
    operation_mode_from_api,
    power_save_from_api,
)
from .const import (
    OPT_ENABLE_HEAT_PUMP,
    SLEEP_TIMER_DAY_PROFILES,
    SK_BLOWER,
    SK_DATE_TIME,
    SK_ELEMENT_BOOST,
    SK_ELEMENT_BOOST_SUPPORTED,
    SK_FILTRATION_CYCLE,
    SK_FILTRATION_RUNTIME,
    SK_HEATER,
    SK_HEAT_PUMP,
    SK_LIGHTS,
    SK_LIGHT_ANIMATION,
    SK_LIGHT_PROFILE,
    SK_OPERATION_MODE,
    SK_POWER_SAVE,
    SK_PUMPS,
    SK_SANITISE,
    SK_SANITISE_STATUS,
    SK_SANITISE_TIME,
    SK_SETTEMP,
    SK_SLEEP_TIMERS,
    SK_SLEEPING,
    SK_TIMEOUT,
    SK_WATERTEMP,
    SL_HEATING,
    SL_SANITISE,
    SL_SLEEPING,
)
from .scheduler import Scheduler
from .spanet import SpaNetApiError

logger = logging.getLogger(__name__)


class Coordinator(DataUpdateCoordinator):
    """SpaNET state coordinator."""

    def __init__(self, hass, spanet, spa_config, config_entry):
        super().__init__(
            hass,
            logger,
            name=spa_config["name"],
            update_interval=timedelta(seconds=60),
        )
        self.spanet = spanet
        self.spa_config = spa_config
        self.config_entry = config_entry
        self.state = {}
        self.spa = None
        self.device = None

        self.scheduler = Scheduler()
        self.tasks = [
            self.scheduler.add_task(120, self.update_dashboard),
            self.scheduler.add_task(300, self.update_pumps),
            self.scheduler.add_task(1200, self.update_information),
            self.scheduler.add_task(300, self.update_lights),
            self.scheduler.add_task(600, self.update_settings),
        ]

    @property
    def spa_name(self):
        return self.spa_config["name"]

    @property
    def spa_id(self):
        return self.spa_config["id"]

    def queue_refresh(self):
        self.tasks[0].trigger(20)

    def queue_information_refresh(self):
        self.tasks[2].trigger(0)

    def queue_lights_refresh(self):
        self.tasks[3].trigger(0)

    def queue_settings_refresh(self):
        self.tasks[4].trigger(0)

    def get_state(self, key: str, sub_key=None):
        obj = self.state
        path = key.split(".")
        if sub_key is not None:
            path.append(sub_key)
        try:
            for p in path:
                obj = obj[p]
            return obj
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Failed to load data for status key %s", key, exc_info=exc)
            logger.error("Status: %s", self.state)
            raise

    def get_state_numeric(self, key: str, divisor=1):
        try:
            value = self.get_state(key)
        except Exception:
            return None
        if value is None:
            return None
        return int(value) / divisor

    async def set_temperature(self, temp: int):
        self.state[SK_SETTEMP] = temp
        await self.spa.set_temperature(temp)
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_pump(self, key: str, state: str):
        pump = self.get_state(f"{SK_PUMPS}.{key}")
        normalized = str(state).lower()
        if pump.get("auto", False):
            if normalized not in PUMP_SELECT_OPTIONS:
                logger.warning("Unsupported auto-capable pump state %s for pump %s", normalized, key)
                return
        elif normalized not in {"on", "off"}:
            logger.warning("Unsupported binary pump state %s for pump %s", normalized, key)
            return
        pump["state"] = normalized
        await self.spa.set_pump(pump["apiId"], normalized)
        self.tasks[1].trigger(0)
        await self.async_request_refresh()

    async def set_lights(self, state: str):
        lights = self.get_state(SK_LIGHTS)
        lights["state"] = state
        await self.spa.set_light_status(lights["apiId"], state == "on")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_light_brightness(self, value: int):
        lights = self.get_state(SK_LIGHTS)
        mapped_value = max(1, min(5, int(value)))
        lights["brightness"] = mapped_value
        await self.spa.set_light_brightness(lights["apiId"], mapped_value)
        self.queue_lights_refresh()
        await self.async_request_refresh()

    async def set_light_speed(self, value: int):
        lights = self.get_state(SK_LIGHTS)
        mapped_value = max(1, min(5, int(value)))
        lights["speed"] = mapped_value
        await self.spa.set_light_speed(lights["apiId"], mapped_value)
        self.queue_lights_refresh()
        await self.async_request_refresh()

    async def set_light_mode(self, mode: str):
        lights = self.get_state(SK_LIGHTS)
        lights["mode"] = mode
        await self.spa.set_light_mode(lights["apiId"], mode)
        self.queue_lights_refresh()
        await self.async_request_refresh()

    async def set_light_profile(self, profile: str):
        if profile not in {"Single", "Animated"}:
            return
        if profile == "Single":
            await self.set_light_mode("Single")
            self.state[SK_LIGHT_PROFILE] = "Single"
            return

        current_animation = self.state.get(SK_LIGHT_ANIMATION)
        mode = current_animation if current_animation in LIGHT_ANIMATION_OPTIONS else "Fade"
        await self.set_light_mode(mode)
        self.state[SK_LIGHT_PROFILE] = "Animated"
        self.state[SK_LIGHT_ANIMATION] = mode

    async def set_light_animation(self, animation: str):
        if animation not in LIGHT_ANIMATION_OPTIONS:
            return
        await self.set_light_mode(animation)
        self.state[SK_LIGHT_PROFILE] = "Animated"
        self.state[SK_LIGHT_ANIMATION] = animation

    async def set_light_colour(self, colour: str):
        lights = self.get_state(SK_LIGHTS)
        lights["colour"] = colour
        await self.spa.set_light_colour(lights["apiId"], colour)
        self.queue_lights_refresh()
        await self.async_request_refresh()

    async def set_operation_mode(self, mode: str):
        from .api_mappings import OPERATION_MODE_API_BY_LABEL

        mode_index = OPERATION_MODE_API_BY_LABEL[mode]
        await self.spa.set_operation_mode(mode_index)
        self.state[SK_OPERATION_MODE] = mode
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_power_save(self, mode: str):
        from .api_mappings import POWER_SAVE_API_BY_LABEL

        mode_index = POWER_SAVE_API_BY_LABEL[mode]
        await self.spa.set_power_save(mode_index)
        self.state[SK_POWER_SAVE] = mode
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_sleep_timer(self, key: str, value: str):
        timer = self.get_state(f"{SK_SLEEP_TIMERS}.{key}")
        timer["state"] = value
        timer["isEnabled"] = value == "on"
        await self.spa.set_sleep_timer_enabled(timer["apiId"], value == "on")
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def _update_sleep_timer_fields(
        self,
        key: str,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        days_hex: str | None = None,
    ):
        timer = self.get_state(f"{SK_SLEEP_TIMERS}.{key}")
        updated_start = start_time if start_time is not None else timer.get("startTime")
        updated_end = end_time if end_time is not None else timer.get("endTime")
        updated_days = days_hex if days_hex is not None else timer.get("daysHex")

        await self.spa.update_sleep_timer(
            timer_id=int(timer["apiId"]),
            timer_number=int(timer["number"]),
            timer_name=str(timer.get("name", f"Timer {key}")),
            start_time=str(updated_start),
            end_time=str(updated_end),
            days_hex=str(updated_days),
            is_enabled=bool(timer.get("isEnabled", timer.get("state") == "on")),
        )

        timer["startTime"] = str(updated_start)
        timer["endTime"] = str(updated_end)
        timer["daysHex"] = str(updated_days)
        timer["dayProfile"] = self._timer_day_profile_from_hex(str(updated_days))
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_sleep_timer_day_profile(self, key: str, profile: str):
        if profile == "Custom":
            return
        days_hex = SLEEP_TIMER_DAY_PROFILES.get(profile)
        if days_hex is None:
            logger.warning("Unknown sleep timer profile '%s' for timer %s", profile, key)
            return
        await self._update_sleep_timer_fields(key, days_hex=days_hex)

    async def set_sleep_timer_on_time(self, key: str, value: str):
        await self._update_sleep_timer_fields(key, start_time=value)

    async def set_sleep_timer_off_time(self, key: str, value: str):
        await self._update_sleep_timer_fields(key, end_time=value)

    async def create_sleep_timer(
        self,
        timer_number: int,
        timer_name: str,
        start_time: str,
        end_time: str,
        days_hex: str,
        is_enabled: bool,
    ):
        await self.spa.create_sleep_timer(
            timer_number=timer_number,
            timer_name=timer_name,
            start_time=start_time,
            end_time=end_time,
            days_hex=days_hex,
            is_enabled=is_enabled,
        )
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def update_sleep_timer(
        self,
        timer_id: int,
        timer_number: int,
        timer_name: str,
        start_time: str,
        end_time: str,
        days_hex: str,
        is_enabled: bool,
    ):
        await self.spa.update_sleep_timer(
            timer_id=timer_id,
            timer_number=timer_number,
            timer_name=timer_name,
            start_time=start_time,
            end_time=end_time,
            days_hex=days_hex,
            is_enabled=is_enabled,
        )
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def delete_sleep_timer(self, timer_id: int):
        await self.spa.delete_sleep_timer(timer_id)
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_heat_pump(self, mode: str):
        await self.spa.set_heat_pump(mode)
        self.state[SK_HEAT_PUMP] = mode
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_sanitiser(self, value: str):
        if str(value).lower() != "on":
            logger.info("Ignoring sanitise '%s' request for spa %s; sanitise is a trigger action", value, self.spa_id)
            return
        on = value == "on"
        try:
            await self.spa.set_sanitise_status(on)
            sanitise_status = await self.spa.get_sanitise_status()
            self.state[SK_SANITISE_STATUS] = "on" if bool(sanitise_status) else "off"
        except SpaNetApiError as exc:
            logger.warning("Failed to set sanitise status for spa %s: %s", self.spa_id, exc)
            return
        self.queue_refresh()
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def trigger_sanitise(self):
        await self.set_sanitiser("on")

    async def set_sanitise_time(self, value: str):
        await self.spa.set_sanitise_time(value)
        self.state[SK_SANITISE_TIME] = value
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_date_time(self, value: str):
        await self.spa.set_date_time(value)
        self.state[SK_DATE_TIME] = value
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_element_boost(self, value: str):
        if not self.state.get(SK_ELEMENT_BOOST_SUPPORTED, False):
            logger.warning("Element Boost not supported for spa %s", self.spa_id)
            return

        on = value == "on"
        try:
            await self.spa.set_element_boost(on)
        except SpaNetApiError as exc:
            logger.warning("Failed to set Element Boost for spa %s: %s", self.spa_id, exc)
            return

        self.state[SK_ELEMENT_BOOST] = "on" if on else "off"
        self.queue_information_refresh()
        await self.async_request_refresh()

    async def set_blower(self, value: str):
        blower = self.get_state(SK_BLOWER)
        normalized = str(value).lower()
        blower["state"] = normalized
        await self.spa.set_blower(blower["apiId"], normalized, int(blower.get("speed", 1)))
        self.tasks[1].trigger(0)
        await self.async_request_refresh()

    async def set_blower_switch(self, value: str):
        target_state = "off" if str(value).lower() == "off" else "variable"
        await self.set_blower(target_state)

    async def set_blower_speed(self, value: int):
        blower = self.get_state(SK_BLOWER)
        blower["speed"] = max(1, min(5, int(value)))
        state = blower.get("state", "variable")
        if state != "variable":
            state = "variable"
            blower["state"] = state
        await self.spa.set_blower(blower["apiId"], state, blower["speed"])
        self.tasks[1].trigger(0)
        await self.async_request_refresh()

    async def set_filtration_runtime(self, value: int):
        current_cycle = int(self.state.get(SK_FILTRATION_CYCLE, 0))
        self.state[SK_FILTRATION_RUNTIME] = value
        await self.spa.set_filtration(total_runtime=value, in_between_cycles=current_cycle)
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_filtration_cycle(self, value: int):
        current_runtime = int(self.state.get(SK_FILTRATION_RUNTIME, 0))
        self.state[SK_FILTRATION_CYCLE] = value
        await self.spa.set_filtration(total_runtime=current_runtime, in_between_cycles=value)
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def set_lock_mode_switch(self, value: str):
        return

    async def set_timeout(self, value: int):
        self.state[SK_TIMEOUT] = value
        await self.spa.set_timeout(value)
        self.queue_settings_refresh()
        await self.async_request_refresh()

    async def _async_update_data(self):
        try:
            if not self.spa:
                self.spa = await self.spanet.get_spa(self.spa_id)
            async with async_timeout.timeout(10):
                await self.refresh_state()
        except SpaNetApiError as exc:
            logger.error("API Error: %s", exc)
            raise UpdateFailed("Failed updating spanet") from exc

    async def refresh_state(self):
        await self.scheduler.tick()
        logger.debug("Spa %s Status: %s", self.spa_id, self.state)

    async def update_dashboard(self):
        dashboard_data = await self.spa.get_dashboard()
        self.state[SK_SETTEMP] = dashboard_data.get("setTemperature")
        self.state[SK_WATERTEMP] = dashboard_data.get("currentTemperature")

        status_list = [s.split(" ")[0] for s in dashboard_data.get("statusList", [])]
        force_refresh = self.state.get("statusList") != status_list
        self.state["statusList"] = status_list

        self.state[SK_HEATER] = 1 if SL_HEATING in status_list else 0
        self.state[SK_SLEEPING] = 1 if SL_SLEEPING in status_list else 0
        self.state[SK_SANITISE] = 1 if SL_SANITISE in status_list else 0

        if force_refresh:
            for task in self.tasks[1:]:
                task.trigger()

    async def update_pumps(self):
        pump_data = await self.spa.get_pumps()
        details = pump_data.get("pumpAndBlower", {})

        pumps = self.state.get(SK_PUMPS, {})
        for p in details.get("pumps", []):
            pump_id = str(p["pumpNumber"])
            if pump_id not in pumps:
                pumps[pump_id] = {}
            pump = pumps[pump_id]
            raw_state = str(p.get("pumpStatus", "off")).lower()
            if raw_state == "auto":
                normalized_state = "auto"
            elif raw_state in {"on", "high", "low", "1"}:
                normalized_state = "on"
            else:
                normalized_state = "off"
            pump["apiId"] = str(p["id"])
            pump["auto"] = bool(p.get("hasAuto", False))
            pump["speeds"] = int(p.get("pumpSpeed", 1))
            pump["hasSwitch"] = bool(p.get("canSwitchOn", False))
            pump["state"] = normalized_state
        self.state[SK_PUMPS] = pumps

        blower_data = details.get("blower") or {}
        if blower_data:
            raw_state = str(blower_data.get("blowerStatus", "off")).lower()
            speed = int(blower_data.get("speed", 1) or 1)
            if raw_state in {"auto", "ramp"}:
                mapped_state = "ramp"
            elif raw_state in {"on", "variable", "low", "high"}:
                mapped_state = "variable"
            else:
                mapped_state = "off"
            self.state[SK_BLOWER] = {
                "apiId": str(blower_data.get("id")),
                "state": mapped_state,
                "speed": max(1, min(5, speed)),
            }

    async def update_information(self):
        information_data = await self.spa.get_information()
        settings_summary = information_data.get("information", {}).get("settingsSummary", {})

        element_boost = settings_summary.get("hpElementBoost")
        is_supported = element_boost is not None
        self.state[SK_ELEMENT_BOOST_SUPPORTED] = is_supported
        if is_supported:
            self.state[SK_ELEMENT_BOOST] = (
                "on" if str(element_boost).lower() in {"1", "true"} else "off"
            )
        elif SK_ELEMENT_BOOST not in self.state:
            self.state[SK_ELEMENT_BOOST] = None

    async def update_lights(self):
        light_details = await self.spa.get_light_details()
        brightness = light_details.get("brightness", light_details.get("lightBrightness", 0))
        speed = light_details.get("speed", light_details.get("lightSpeed", 0))
        self.state[SK_LIGHTS] = {
            "apiId": light_details.get("lightId"),
            "state": "on" if light_details.get("lightOn") else "off",
            "brightness": max(1, min(5, int(brightness or 1))),
            "speed": max(1, min(5, int(speed or 1))),
            "mode": light_details.get("mode", light_details.get("lightMode")),
            "colour": light_details.get("colour", light_details.get("lightColour")),
        }
        mode = str(self.state[SK_LIGHTS].get("mode") or "")
        if mode in LIGHT_ANIMATION_OPTIONS:
            self.state[SK_LIGHT_PROFILE] = "Animated"
            self.state[SK_LIGHT_ANIMATION] = mode
        else:
            self.state[SK_LIGHT_PROFILE] = "Single"
            self.state[SK_LIGHT_ANIMATION] = "Fade"

    async def update_settings(self):
        filtration = await self.spa.get_filtration()
        self.state[SK_FILTRATION_RUNTIME] = int(filtration.get("totalRuntime", 0))
        self.state[SK_FILTRATION_CYCLE] = int(filtration.get("inBetweenCycles", 0))

        try:
            self.state[SK_TIMEOUT] = int(await self.spa.get_timeout())
        except (TypeError, ValueError):
            self.state[SK_TIMEOUT] = None

        sanitise_time = await self.spa.get_sanitise_time()
        self.state[SK_SANITISE_TIME] = extract_time_string(sanitise_time)

        sanitise_status = await self.spa.get_sanitise_status()
        self.state[SK_SANITISE_STATUS] = "on" if bool(sanitise_status) else "off"

        try:
            sleep_timers = await self.spa.get_sleep_timer()
        except Exception:
            sleep_timers = []

        timers = {}
        for t in sleep_timers:
            timer_id = str(t.get("timerNumber"))
            if not timer_id:
                continue
            timers[timer_id] = {
                "id": t.get("id"),
                "number": t.get("timerNumber"),
                "apiId": t.get("id"),
                "name": t.get("timerName"),
                "startTime": extract_time_string(t.get("startTime")),
                "endTime": extract_time_string(t.get("endTime")),
                "daysHex": t.get("daysHex"),
                "dayProfile": self._timer_day_profile_from_hex(str(t.get("daysHex", ""))),
                "isEnabled": bool(t.get("isEnabled")),
                "state": "on" if t.get("isEnabled") else "off",
            }
        self.state[SK_SLEEP_TIMERS] = timers

        try:
            power_save = await self.spa.get_power_save()
            self.state[SK_POWER_SAVE] = power_save_from_api(power_save.get("mode"))
        except AttributeError:
            pass

        try:
            operation_mode = await self.spa.get_operation_mode()
            self.state[SK_OPERATION_MODE] = operation_mode_from_api(operation_mode)
        except (TypeError, ValueError, AttributeError):
            pass

        if self.config_entry.options.get(OPT_ENABLE_HEAT_PUMP, False):
            try:
                heat_pump = await self.spa.get_heat_pump()
                self.state[SK_HEAT_PUMP] = heat_pump_from_api(heat_pump.get("mode"))
            except (TypeError, ValueError, AttributeError):
                self.state[SK_HEAT_PUMP] = "Off"

    @staticmethod
    def fuzzy_find(modes, mode):
        if mode is None:
            return None
        for m in modes:
            if m.lower().startswith(str(mode).lower()):
                return m
        return None

    @staticmethod
    def _timer_day_profile_from_hex(days_hex: str) -> str:
        for profile, value in SLEEP_TIMER_DAY_PROFILES.items():
            if value.lower() == str(days_hex).lower():
                return profile
        return "Custom"
