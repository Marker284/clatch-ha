"""Сенсоры Clatch: день цикла, фаза, дни до событий, дневник."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ClatchDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class ClatchSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSOR_TYPES: tuple[ClatchSensorEntityDescription, ...] = (
    ClatchSensorEntityDescription(
        key="cycle_day",
        translation_key="cycle_day",
        icon="mdi:calendar-heart",
        native_unit_of_measurement="д.",
        value_fn=lambda d: d["cycle_day"],
        attrs_fn=lambda d: {"cycle_length": d["cycle_length"]},
    ),
    ClatchSensorEntityDescription(
        key="phase",
        translation_key="phase",
        icon="mdi:moon-waning-crescent",
        value_fn=lambda d: d["phase_title"],
        attrs_fn=lambda d: {"phase_key": d["phase_key"], "note": d["phase_note"]},
    ),
    ClatchSensorEntityDescription(
        key="days_until_period",
        translation_key="days_until_period",
        icon="mdi:calendar-clock",
        native_unit_of_measurement="д.",
        value_fn=lambda d: d["days_until_period"],
    ),
    ClatchSensorEntityDescription(
        key="days_until_period_end",
        translation_key="days_until_period_end",
        icon="mdi:calendar-check",
        native_unit_of_measurement="д.",
        value_fn=lambda d: d["days_until_period_end"] if d["is_period_now"] else None,
    ),
    ClatchSensorEntityDescription(
        key="days_until_ovulation",
        translation_key="days_until_ovulation",
        icon="mdi:egg",
        native_unit_of_measurement="д.",
        value_fn=lambda d: d["days_until_ovulation"],
    ),
    ClatchSensorEntityDescription(
        key="next_period_start",
        translation_key="next_period_start",
        icon="mdi:calendar-arrow-right",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda d: d["next_period_start"],
    ),
    ClatchSensorEntityDescription(
        key="ovulation_date",
        translation_key="ovulation_date",
        icon="mdi:calendar-star",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda d: d["ovulation_date"],
    ),
    ClatchSensorEntityDescription(
        key="last_period_start",
        translation_key="last_period_start",
        icon="mdi:calendar-start",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda d: d["last_period_start"],
    ),
    ClatchSensorEntityDescription(
        key="avg_period_length",
        translation_key="avg_period_length",
        icon="mdi:calendar-range",
        native_unit_of_measurement="д.",
        value_fn=lambda d: d["avg_period_length"],
        attrs_fn=lambda d: {"cycle_lengths_recent": d["cycle_lengths_recent"]},
    ),
    ClatchSensorEntityDescription(
        key="last_diary_entry",
        translation_key="last_diary_entry",
        icon="mdi:notebook-heart",
        value_fn=lambda d: (d["last_diary_entry"]["date"][:10] if d.get("last_diary_entry") else None),
        attrs_fn=lambda d: (
            {
                "symptoms": d["last_diary_entry"]["symptoms"],
                "cycle_day": d["last_diary_entry"]["cycleDay"],
            }
            if d.get("last_diary_entry")
            else {}
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClatchDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(ClatchSensor(coordinator, entry, description) for description in SENSOR_TYPES)


class ClatchSensor(CoordinatorEntity[ClatchDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: ClatchSensorEntityDescription

    def __init__(
        self,
        coordinator: ClatchDataUpdateCoordinator,
        entry: ConfigEntry,
        description: ClatchSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get("name", "Clatch"),
            manufacturer="Неофициальный API (реверс-инжиниринг)",
            model="Clatch Cycle Tracker",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.entity_description.attrs_fn is None:
            return {}
        return self.entity_description.attrs_fn(self.coordinator.data)
