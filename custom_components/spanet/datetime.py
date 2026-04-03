"""SpaNET datetime entities."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SK_DATE_TIME
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entity: AddEntitiesCallback,
) -> bool:
    entities = []
    for coordinator in hass.data[DOMAIN][config_entry.entry_id]["coordinators"]:
        entities.append(
            SpaDateTime(
                coordinator,
                "Date/Time",
                SK_DATE_TIME,
                coordinator.set_date_time,
            )
        )
    async_add_entity(entities)
    return True


class SpaDateTime(SpaEntity, DateTimeEntity):
    """Spa date/time setting."""

    def __init__(self, coordinator, name: str, state_key: str, setter):
        super().__init__(coordinator, "datetime", name)
        self._state_key = state_key
        self._setter = setter
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> datetime | None:
        try:
            value = self.coordinator.get_state(self._state_key)
        except Exception:
            return None
        if not value:
            return None
        parsed = dt_util.parse_datetime(str(value))
        if parsed is not None:
            return parsed
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(str(value), fmt).replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            except ValueError:
                continue
        return None

    async def async_set_value(self, value: datetime) -> None:
        local_dt = dt_util.as_local(value)
        await self._setter(local_dt.strftime("%Y-%m-%d %H:%M:%S"))
