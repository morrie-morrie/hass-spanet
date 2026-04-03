import logging
from datetime import timedelta

import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    HEAT_PUMP,
    OPERATION_MODES,
    OPT_ENABLE_HEAT_PUMP,
    POWER_SAVE,
    SK_BLOWER,
    SK_ELEMENT_BOOST,
    SK_ELEMENT_BOOST_SUPPORTED,
    SK_FILTRATION_CYCLE,
    SK_FILTRATION_RUNTIME,
    SK_HEATER,
    SK_HEAT_PUMP,
    SK_LIGHTS,
    SK_LOCK_MODE,
    SK_OPERATION_MODE,
    SK_OXY,
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
        value = self.get_state(key)
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
        pump["state"] = state
        await self.spa.set_pump(pump["apiId"], state)
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_lights(self, state: str):
        lights = self.get_state(SK_LIGHTS)
        lights["state"] = state
        await self.spa.set_light_status(lights["apiId"], state == "on")
        await self.async_request_refresh()
        self.queue_refresh()

    async def set_light_brightness(self, value: int):
        lights = self.get_state(SK_LIGHTS)
        lights["brightness"] = value
        await self.spa.set_light_brightness(lights["apiId"], value)
        await self.async_request_refresh()

    async def set_light_speed(self, value: int):
        lights = self.get_state(SK_LIGHTS)
        lights["speed"] = value
        await self.spa.set_light_speed(lights["apiId"], value)
        await self.async_request_refresh()

    async def set_light_mode(self, mode: str):
        lights = self.get_state(SK_LIGHTS)
        lights["mode"] = mode
        await self.spa.set_light_mode(lights["apiId"], mode)
        await self.async_request_refresh()

    async def set_light_colour(self, colour: str):
        lights = self.get_state(SK_LIGHTS)
        lights["colour"] = colour
        await self.spa.set_light_colour(lights["apiId"], colour)
        await self.async_request_refresh()

    async def set_operation_mode(self, mode: str):
        mode_index = OPERATION_MODES.index(mode)
        await self.spa.set_operation_mode(mode_index)
        self.state[SK_OPERATION_MODE] = mode
        await self.async_request_refresh()

    async def set_power_save(self, mode: str):
        mode_index = POWER_SAVE.index(mode)
        await self.spa.set_power_save(mode_index)
        self.state[SK_POWER_SAVE] = mode
        await self.async_request_refresh()

    async def set_sleep_timer(self, key: str, value: str):
        timer = self.get_state(f"{SK_SLEEP_TIMERS}.{key}")
        timer["state"] = value
        await self.spa.set_sleep_timer_enabled(timer["apiId"], value == "on")
        await self.async_request_refresh()

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
        self.tasks[2].trigger(0)
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
        self.tasks[2].trigger(0)
        await self.async_request_refresh()

    async def delete_sleep_timer(self, timer_id: int):
        await self.spa.delete_sleep_timer(timer_id)
        self.tasks[2].trigger(0)
        await self.async_request_refresh()

    async def set_heat_pump(self, mode: str):
        mode_index = HEAT_PUMP.index(mode)
        await self.spa.set_heat_pump(mode_index)
        self.state[SK_HEAT_PUMP] = mode
        await self.async_request_refresh()

    async def set_sanitiser(self, value: str):
        on = value == "on"
        await self.spa.set_sanitise_status(on)
        self.state[SK_SANITISE_STATUS] = "on" if on else "off"
        await self.async_request_refresh()

    async def set_sanitise_time(self, value: str):
        await self.spa.set_sanitise_time(value)
        self.state[SK_SANITISE_TIME] = value
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
        await self.async_request_refresh()

    async def set_oxy(self, value: str):
        on = value == "on"
        await self.spa.set_oxy(on)
        self.state[SK_OXY] = "on" if on else "off"
        await self.async_request_refresh()

    async def set_blower(self, value: str):
        blower = self.get_state(SK_BLOWER)
        blower["state"] = value
        await self.spa.set_blower(blower["apiId"], value, int(blower.get("speed", 0)))
        await self.async_request_refresh()

    async def set_blower_speed(self, value: int):
        blower = self.get_state(SK_BLOWER)
        blower["speed"] = value
        await self.spa.set_blower(blower["apiId"], blower.get("state", "on"), value)
        await self.async_request_refresh()

    async def set_filtration_runtime(self, value: int):
        current_cycle = int(self.state.get(SK_FILTRATION_CYCLE, 0))
        self.state[SK_FILTRATION_RUNTIME] = value
        await self.spa.set_filtration(total_runtime=value, in_between_cycles=current_cycle)
        await self.async_request_refresh()

    async def set_filtration_cycle(self, value: int):
        current_runtime = int(self.state.get(SK_FILTRATION_RUNTIME, 0))
        self.state[SK_FILTRATION_CYCLE] = value
        await self.spa.set_filtration(total_runtime=current_runtime, in_between_cycles=value)
        await self.async_request_refresh()

    async def set_lock_mode(self, value: int):
        self.state[SK_LOCK_MODE] = value
        await self.spa.set_lock_mode(value)
        await self.async_request_refresh()

    async def set_timeout(self, value: int):
        self.state[SK_TIMEOUT] = value
        await self.spa.set_timeout(value)
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
            pump["apiId"] = str(p["id"])
            pump["auto"] = p.get("hasAuto", False)
            pump["speeds"] = int(p.get("pumpSpeed", 1))
            pump["hasSwitch"] = p.get("canSwitchOn", False) and (
                not p.get("hasAuto", False) or int(p.get("pumpSpeed", 1)) > 1
            )
            pump["state"] = str(p.get("pumpStatus", "off")).lower()
        self.state[SK_PUMPS] = pumps

        blower_data = details.get("blower") or {}
        if blower_data:
            self.state[SK_BLOWER] = {
                "apiId": str(blower_data.get("id")),
                "state": str(blower_data.get("blowerStatus", "off")).lower(),
                "speed": int(blower_data.get("speed", 0)),
            }

        oxy = details.get("oxy")
        if oxy is not None:
            self.state[SK_OXY] = "on" if bool(oxy) else "off"

    async def update_information(self):
        information_data = await self.spa.get_information()
        settings_summary = information_data.get("information", {}).get("settingsSummary", {})

        operation_mode = self.fuzzy_find(OPERATION_MODES, settings_summary.get("operationMode"))
        self.state[SK_OPERATION_MODE] = operation_mode or OPERATION_MODES[0]

        try:
            power_save = int(settings_summary.get("powersaveTimer", {}).get("mode"))
            self.state[SK_POWER_SAVE] = POWER_SAVE[power_save]
        except (TypeError, ValueError, IndexError):
            self.state[SK_POWER_SAVE] = POWER_SAVE[0]

        if self.config_entry.options.get(OPT_ENABLE_HEAT_PUMP, False):
            try:
                heat_pump = int(settings_summary.get("heatPumpMode"))
                self.state[SK_HEAT_PUMP] = HEAT_PUMP[heat_pump]
            except (TypeError, ValueError, IndexError):
                self.state[SK_HEAT_PUMP] = HEAT_PUMP[-1]
        else:
            self.state[SK_HEAT_PUMP] = "Off"

        element_boost = settings_summary.get("hpElementBoost")
        is_supported = element_boost is not None
        self.state[SK_ELEMENT_BOOST_SUPPORTED] = is_supported
        if is_supported:
            self.state[SK_ELEMENT_BOOST] = (
                "on" if str(element_boost).lower() in {"1", "true"} else "off"
            )
        elif SK_ELEMENT_BOOST not in self.state:
            self.state[SK_ELEMENT_BOOST] = None

        timers = {}
        for t in settings_summary.get("sleepTimers", []):
            timer_id = str(t["timerNumber"])
            timers[timer_id] = {
                "id": t.get("id"),
                "number": t.get("timerNumber"),
                "apiId": t.get("id"),
                "name": t.get("timerName"),
                "startTime": t.get("startTime"),
                "endTime": t.get("endTime"),
                "daysHex": t.get("daysHex"),
                "isEnabled": bool(t.get("isEnabled")),
                "state": "on" if t.get("isEnabled") else "off",
            }
        self.state[SK_SLEEP_TIMERS] = timers

    async def update_lights(self):
        light_details = await self.spa.get_light_details()
        brightness = light_details.get("brightness", light_details.get("lightBrightness", 0))
        speed = light_details.get("speed", light_details.get("lightSpeed", 0))
        self.state[SK_LIGHTS] = {
            "apiId": light_details.get("lightId"),
            "state": "on" if light_details.get("lightOn") else "off",
            "brightness": int(brightness or 0),
            "speed": int(speed or 0),
            "mode": light_details.get("mode", light_details.get("lightMode")),
            "colour": light_details.get("colour", light_details.get("lightColour")),
        }

    async def update_settings(self):
        filtration = await self.spa.get_filtration()
        self.state[SK_FILTRATION_RUNTIME] = int(filtration.get("totalRuntime", 0))
        self.state[SK_FILTRATION_CYCLE] = int(filtration.get("inBetweenCycles", 0))

        try:
            self.state[SK_LOCK_MODE] = int(await self.spa.get_lock_mode())
        except (TypeError, ValueError):
            self.state[SK_LOCK_MODE] = 0

        try:
            self.state[SK_TIMEOUT] = int(await self.spa.get_timeout())
        except (TypeError, ValueError):
            self.state[SK_TIMEOUT] = 0

        sanitise_time = await self.spa.get_sanitise_time()
        self.state[SK_SANITISE_TIME] = sanitise_time

        sanitise_status = await self.spa.get_sanitise_status()
        self.state[SK_SANITISE_STATUS] = "on" if bool(sanitise_status) else "off"

        try:
            power_save = await self.spa.get_power_save()
            mode = int(power_save.get("mode"))
            self.state[SK_POWER_SAVE] = POWER_SAVE[mode]
        except (TypeError, ValueError, IndexError, AttributeError):
            pass

    @staticmethod
    def fuzzy_find(modes, mode):
        if mode is None:
            return None
        for m in modes:
            if m.lower().startswith(str(mode).lower()):
                return m
        return None
