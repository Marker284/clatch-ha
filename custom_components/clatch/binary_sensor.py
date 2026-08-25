"""Бинарный сенсор — идут ли сейчас месячные."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ClatchDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClatchDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ClatchPeriodActiveBinarySensor(coordinator, entry)])


class ClatchPeriodActiveBinarySensor(CoordinatorEntity[ClatchDataUpdateCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "period_active"
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: ClatchDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_period_active"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get("name", "Clatch"),
            manufacturer="Неофициальный API (реверс-инжиниринг)",
            model="Clatch Cycle Tracker",
        )

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("is_period_now"))
