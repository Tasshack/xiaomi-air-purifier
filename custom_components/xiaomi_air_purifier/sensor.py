"""Support for Xiaomi Air Purifier sensors."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    UNIT_HOURS,
    UNIT_AREA,
    UNIT_DAYS,
    FAN_LEVEL_TO_ICON,
)
from .xiaomi import (
    XiaomiAirPurifierProperty,
    XiaomiAirPurifierAirQuality,
    XiaomiAirPurifierDoorStatus,    
    XiaomiAirPurifierTemperatureUnit,
    XiaomiAirPurifierMode,
)

from homeassistant.const import PERCENTAGE, CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, REVOLUTIONS_PER_MINUTE

from .coordinator import XiaomiAirPurifierDataUpdateCoordinator
from .entity import XiaomiAirPurifierEntity, XiaomiAirPurifierEntityDescription

AIR_QUALITY_TO_ICON = {
    XiaomiAirPurifierAirQuality.UNKNOWN: "mdi:card-outline",
    XiaomiAirPurifierAirQuality.EXCELLENT: "mdi:transfer-up",
    XiaomiAirPurifierAirQuality.GOOD: "mdi:chevron-triple-up",
    XiaomiAirPurifierAirQuality.MODERATE: "mdi:chevron-double-up",
    XiaomiAirPurifierAirQuality.POOR: "mdi:chevron-double-down",
    XiaomiAirPurifierAirQuality.UNHEALTY: "mdi:chevron-triple-down",
    XiaomiAirPurifierAirQuality.HAZARDOUS: "mdi:alert-octagon",
}

DOOR_STATUS_TO_ICON = {
    XiaomiAirPurifierDoorStatus.OPEN: "mdi:door-open",
    XiaomiAirPurifierDoorStatus.CLOSED: "mdi:door-closed",
}

@dataclass
class XiaomiAirPurifierSensorEntityDescription(
    XiaomiAirPurifierEntityDescription, SensorEntityDescription
):
    """Describes XiaomiAirPurifier sensor entity."""


SENSORS: tuple[XiaomiAirPurifierSensorEntityDescription, ...] = (
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.TEMPERATURE,
        unit_fn=lambda value, device: "°C" if device.status.temperature_unit is XiaomiAirPurifierTemperatureUnit.CELCIUS else "°F",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),   
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.PM2_5,
        name="PM2.5",
        icon="mdi:shimmer",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,        
        suggested_display_precision=0,
    ), 
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.AVERAGE_PM2_5,
        name="Average PM2.5",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        icon="mdi:chart-timeline-variant-shimmer",
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,        
        entity_category=EntityCategory.DIAGNOSTIC,
    ), 
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.FILTER_LIFE_LEFT,
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),  
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.FILTER_LEFT_TIME,
        icon="mdi:air-filter",
        native_unit_of_measurement=UNIT_DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),  
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.FILTER_USED_TIME,
        icon="mdi:timer-outline",
        native_unit_of_measurement=UNIT_HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),  
    #XiaomiAirPurifierSensorEntityDescription(
    #    property_key=XiaomiAirPurifierProperty.FILTER_USE,
    #    icon="mdi:clock-outline",
    #    native_unit_of_measurement=UNIT_HOURS,
    #    state_class=SensorStateClass.TOTAL_INCREASING,
    #    entity_category=EntityCategory.DIAGNOSTIC,
    #),      
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.FAN_LEVEL,
        device_class=f"{DOMAIN}__fan_level",        
        icon_fn=lambda value, device: "mdi:sleep" if device.status.sleep_mode else "mdi:fan-off" if device.status.favorite_mode else FAN_LEVEL_TO_ICON.get(device.status.fan_level.value, "mdi:fan"),
    ),
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.FAN_SPEED,
        icon="mdi:wind-power",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
    ),  
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.FAN_SET_SPEED,
        icon="mdi:car-turbocharger",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),  
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.CLEANED_AREA,        
        icon="mdi:set-square",
        native_unit_of_measurement=UNIT_AREA,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ), 
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.AIR_QUALITY,
        device_class=f"{DOMAIN}__air_quality",
        icon_fn=lambda value, device: AIR_QUALITY_TO_ICON.get(device.status.air_quality),
    ),
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.DOOR_STATUS,
        device_class=f"{DOMAIN}__door_status",
        icon_fn=lambda value, device: DOOR_STATUS_TO_ICON.get(device.status.door_status, "mdi:door"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.FAULT,
        device_class=f"{DOMAIN}__fault",
        icon_fn=lambda value, device: "mdi:alert-outline"
        if device.status.has_error
        else "mdi:check-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    XiaomiAirPurifierSensorEntityDescription(
        property_key=XiaomiAirPurifierProperty.RFID_TAG,
        icon="mdi:nfc-variant",
        attrs_fn=lambda device: device.status.rfid,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaomi Air Purifier sensor based on a config entry."""
    coordinator: XiaomiAirPurifierDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]
    async_add_entities(
        XiaomiAirPurifierSensorEntity(coordinator, description)
        for description in SENSORS
        if description.exists_fn(description, coordinator.device)
    )


class XiaomiAirPurifierSensorEntity(XiaomiAirPurifierEntity, SensorEntity):
    """Defines a Xiaomi Air Purifier sensor entity."""

    def __init__(
        self,
        coordinator: XiaomiAirPurifierDataUpdateCoordinator,
        description: XiaomiAirPurifierSensorEntityDescription,
    ) -> None:
        """Initialize a Xiaomi Air Purifier sensor entity."""
        super().__init__(coordinator, description)

        if description.property_key is not None and description.value_fn is None:
            prop = f"{description.property_key.name.lower()}_name"
            if hasattr(coordinator.device.status, prop):
                description.value_fn = lambda value, device: getattr(
                    device.status, prop
                )
