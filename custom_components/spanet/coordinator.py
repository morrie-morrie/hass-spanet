import logging
from datetime import timedelta
import async_timeout
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import *
from .spanet import SpaNetApiError
from .scheduler import Scheduler

logger = logging.getLogger(__name__)

class Coordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, spanet, spa_config):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            logger,
            name=spa_config["name"],
            update_interval=timedelta(seconds=60),
        )
        self.spanet = spanet
        self.spa_config = spa_config
        self.state = {}
        self.spa = None

        self.scheduler = Scheduler()

        dashboard_task = self.scheduler.add_task(120, self.update_dashboard)
        self.tasks = [
            self.scheduler.add_task(300, self.update_pumps),
            self.scheduler.add_task(1200, self.update_operation_mode)
        ]

    @property
    def spa_name(self):
        return self.spa_config["name"]

    @property
    def spa_id(self):
        return self.spa_config["id"]

    def get_state(self, key: str, sub_key=None):
        obj = self.state
        path = key.split('.')
        if sub_key is not None:
            path.append(sub_key)
        try:
            for p in path:
                obj = obj[p]
            return obj
        except (KeyError, IndexError) as exc:
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
        logger.debug(f"SET TEMP: {temp} -> {self.state}")
        await self.async_request_refresh()

    async def set_pump(self, key: str, state: str):
        pump = self.get_state(key)
        pump["state"] = state
        await self.spa.set_pump(pump["apiId"], state)
        logger.debug(f"SET PUMP {key}: {state} -> {self.state}")
        await self.async_request_refresh()

    async def set_operation_mode(self, mode: str):
        modeIndex = OPERATION_MODES.index(mode)
        if modeIndex < 0:
            logger.error(f"Unknown operation mode: {mode}")
            return

        await self.spa.set_operation_mode(modeIndex)
        self.state[SK_OPERATION_MODE] = mode
        logger.debug(f"SET OPERATION MODE: {mode} -> {self.state}")
        await self.async_request_refresh()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            if not self.spa:
                self.spa = await self.spanet.get_spa(self.spa_id)
            async with async_timeout.timeout(10):
                await self.refresh_state()

        except SpaNetApiError as exc:
            logger.error(f"API Error: {exc}")
            raise UpdateFailed("Failed updating spanet") from exc

    async def refresh_state(self):
        await self.scheduler.tick()
        logger.debug(f"Spa {self.spa_id} Status: {self.state}")

    async def update_dashboard(self):
        dashboard_data = await self.spa.get_dashboard()
        logger.debug(f"Update Dashboard {dashboard_data}")

        self.state[SK_SETTEMP] = dashboard_data["setTemperature"]
        self.state[SK_WATERTEMP] = dashboard_data["currentTemperature"]

        status_list = []
        for s in dashboard_data["statusList"]:
            status_list.append(s.split(" ")[0])

        force_refresh = self.state.get("statusList") != status_list

        self.state["statusList"] = status_list

        self.state[SK_HEATER] = 1 if SL_HEATING in status_list else 0
        self.state[SK_SLEEPING] = 1 if SL_SLEEPING in status_list else 0
        self.state[SK_SANITISE] = 1 if SL_SANITISE in status_list else 0

        if force_refresh:
            for task in self.tasks:
                task.trigger()

    async def update_pumps(self):
        pump_data = await self.spa.get_pumps()
        logger.debug(f"Update Pumps {pump_data}")

        pumps = self.state.get("pumps", {})
        for p in pump_data.get("pumpAndBlower", {}).get("pumps", []):
            pump_id = str(p["pumpNumber"])
            if not pump_id in pumps:
                pumps[pump_id] = {}
            pump = pumps.get(pump_id)
            pump["apiId"] = str(p["id"])
            pump["auto"] = p["hasAuto"]
            pump["speeds"] = 1 # p["pumpSpeed"] Multiple speeds not supported
            pump["hasSwitch"] = p["canSwitchOn"] and (not p["hasAuto"] or p["pumpSpeed"] > 1)
            pump["state"] = p["pumpStatus"]

        self.state[SK_PUMPS] = pumps

    async def update_operation_mode(self):
        operation_mode_data = await self.spa.get_operation_mode()
        logger.debug(f"Update Operation Mode {operation_mode_data}")

        self.state[SK_OPERATION_MODE] = OPERATION_MODES[int(operation_mode_data)]

