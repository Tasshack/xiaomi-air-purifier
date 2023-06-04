"""Support for Xiaomi Air Purifier selects."""
from __future__ import annotations

import copy
import voluptuous as vol
from typing import Any
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform, entity_registry

from .const import (
    DOMAIN,
    INPUT_CYCLE,
    SERVICE_SELECT_NEXT,
    SERVICE_SELECT_PREVIOUS,
    SERVICE_SELECT_FIRST,
    SERVICE_SELECT_LAST,
    FAN_LEVEL_TO_ICON
)

from .coordinator import XiaomiAirPurifierDataUpdateCoordinator
from .entity import (
    XiaomiAirPurifierEntity,
    XiaomiAirPurifierEntityDescription,
)

from .xiaomi import (
    XiaomiAirPurifierProperty,
    XiaomiAirPurifierMode,
    XiaomiAirPurifierFanLevel,
    XiaomiAirPurifierScreenBrightness,
    XiaomiAirPurifierTemperatureUnit,
    XiaomiAirPurifierCoverage,
)

MODE_TO_ICON = {
    XiaomiAirPurifierMode.AUTO: "mdi:refresh-auto",
    XiaomiAirPurifierMode.SLEEP: "mdi:power-sleep",
    XiaomiAirPurifierMode.FAVORITE: "mdi:heart",
    XiaomiAirPurifierMode.MANUAL: "mdi:fan",
}

SCREEN_BRIGHTNESS_TO_ICON = {
    XiaomiAirPurifierScreenBrightness.OFF: "mdi:monitor-off",
    XiaomiAirPurifierScreenBrightness.DIM: "mdi:brightness-6",
    XiaomiAirPurifierScreenBrightness.BRIGHT: "mdi:brightness-5",
}

TEMPERATURE_UNIT_TO_ICON = {
    XiaomiAirPurifierTemperatureUnit.CELCIUS: "mdi:temperature-celsius",
    XiaomiAirPurifierTemperatureUnit.FAHRENHEIT: "mdi:temperature-fahrenheit",
}


@dataclass
class XiaomiAirPurifierSelectEntityDescription(
    XiaomiAirPurifierEntityDescription, SelectEntityDescription
):
    """Describes Xiaomi Air Purifier Select entity."""

    set_fn: Callable[[object, str]] = None
    options: Callable[[object], list[str]] = None


SELECTS: tuple[XiaomiAirPurifierSelectEntityDescription, ...] = (
     XiaomiAirPurifierSelectEntityDescription(
        property_key=XiaomiAirPurifierProperty.MODE,
        device_class=f"{DOMAIN}__mode",        
        icon_fn=lambda value, device: FAN_LEVEL_TO_ICON.get(device.status.manual_fan_level.value, "mdi:fan")
        if device.status.manual_mode
        else MODE_TO_ICON.get(device.status.mode, "mdi:fan"),
        options=lambda device: list(device.status.mode_list),
        value_int_fn=lambda value, device: XiaomiAirPurifierMode[value.upper()],
        set_fn=lambda device, value: device.set_mode(value),
    ),
     XiaomiAirPurifierSelectEntityDescription(
        property_key=XiaomiAirPurifierProperty.SCREEN_BRIGHTNESS,
        device_class=f"{DOMAIN}__screen_brightness",        
        icon_fn=lambda value, device: SCREEN_BRIGHTNESS_TO_ICON.get(device.status.screen_brightness, "mdi:monitor"),
        options=lambda device: list(device.status.screen_brightness_list),
        value_int_fn=lambda value, device: XiaomiAirPurifierScreenBrightness[value.upper()],
        entity_category=EntityCategory.CONFIG,
    ),
     XiaomiAirPurifierSelectEntityDescription(
        property_key=XiaomiAirPurifierProperty.TEMPERATURE_UNIT,
        device_class=f"{DOMAIN}__temperature_unit",        
        options=lambda device: list(device.status.temperature_unit_list),
        icon_fn=lambda value, device: TEMPERATURE_UNIT_TO_ICON.get(device.status.temperature_unit, "mdi:sun-thermometer"),
        value_int_fn=lambda value, device: XiaomiAirPurifierTemperatureUnit[value.upper()],
        entity_category=EntityCategory.CONFIG,
    ),
    XiaomiAirPurifierSelectEntityDescription(
        property_key=XiaomiAirPurifierProperty.COVERAGE,
        device_class=f"{DOMAIN}__coverage",
        icon="mdi:ruler-square",
        options=lambda device: list(device.status.coverage_list),
        set_fn=lambda device, value: device.set_coverage(value),
    ),    
    XiaomiAirPurifierSelectEntityDescription(
        property_key=XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL,
        device_class=f"{DOMAIN}__fan_level",
        options=lambda device: list(device.status.fan_level_list),
        icon_fn=lambda value, device: FAN_LEVEL_TO_ICON.get(device.status.manual_fan_level.value, "mdi:fan"),
        set_fn=lambda device, value: device.set_fan_level(value),
        value_int_fn=lambda value, device: XiaomiAirPurifierFanLevel[value.upper()],
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaomi Air Purifier select based on a config entry."""
    coordinator: XiaomiAirPurifierDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        XiaomiAirPurifierSelectEntity(coordinator, description)
        for description in SELECTS
        if description.exists_fn(description, coordinator.device)
    )
    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_SELECT_NEXT,
        {vol.Optional(INPUT_CYCLE, default=True): bool},
        XiaomiAirPurifierSelectEntity.async_next.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_SELECT_PREVIOUS,
        {vol.Optional(INPUT_CYCLE, default=True): bool},
        XiaomiAirPurifierSelectEntity.async_previous.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_SELECT_FIRST, {}, XiaomiAirPurifierSelectEntity.async_first.__name__
    )
    platform.async_register_entity_service(
        SERVICE_SELECT_LAST, {}, XiaomiAirPurifierSelectEntity.async_last.__name__
    )

class XiaomiAirPurifierSelectEntity(XiaomiAirPurifierEntity, SelectEntity):
    """Defines a Xiaomi Air Purifier select."""

    def __init__(
        self,
        coordinator: XiaomiAirPurifierDataUpdateCoordinator,
        description: SelectEntityDescription,
    ) -> None:
        """Initialize Xiaomi Air Purifier select."""
        super().__init__(coordinator, description)            
        if description.property_key is not None and description.value_fn is None:
            prop = f'{description.property_key.name.lower()}_name'
            if hasattr(coordinator.device.status, prop):
                description.value_fn = lambda value, device: getattr(device.status, prop)

        self._attr_options = description.options(coordinator.device)
        self._attr_current_option = self.native_value

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_options = self.entity_description.options(self.device)
        self._attr_current_option = self.native_value
        super()._handle_coordinator_update()

    @callback
    async def async_select_index(self, idx: int) -> None:
        """Select new option by index."""
        new_index = idx % len(self._attr_options)
        await self.async_select_option(self._attr_options[new_index])

    @callback
    async def async_offset_index(self, offset: int, cycle: bool) -> None:
        """Offset current index."""
        current_index = (self._attr_options.index(self._attr_current_option))
        new_index = current_index + offset
        if cycle:
            new_index = new_index % len(self._attr_options)
        elif new_index < 0:
            new_index = 0
        elif new_index >= len(self._attr_options):
            new_index = len(self._attr_options) - 1
        
        if cycle or current_index != new_index:
            await self.async_select_option(self._attr_options[new_index])

    @callback
    async def async_first(self) -> None:
        """Select first option."""
        await self.async_select_index(0)

    @callback
    async def async_last(self) -> None:
        """Select last option."""
        await self.async_select_index(-1)

    @callback
    async def async_next(self, cycle: bool) -> None:
        """Select next option."""
        await self.async_offset_index(1, cycle)

    @callback
    async def async_previous(self, cycle: bool) -> None:
        """Select previous option."""
        await self.async_offset_index(-1, cycle)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if not self.available:
            raise HomeAssistantError("Entity unavailable")

        if option not in self._attr_options:
            raise HomeAssistantError(
                f"Invalid option for {self.entity_description.name} {option}. Valid options: {self._attr_options}"
            )

        value = option
        if self.entity_description.value_int_fn is not None:
            value = self.entity_description.value_int_fn(option, self.device)

        if value is None:
            raise HomeAssistantError(
                f"Invalid option for {self.entity_description.name} {option}. Valid options: {self._attr_options}"
            )

        if self.entity_description.set_fn is not None:
            await self._try_command(
                "Unable to call %s",
                self.entity_description.set_fn,
                self.device,
                int(value),
            )
        elif self.entity_description.property_key is not None:
            await self._try_command(
                "Unable to call %s",
                self.device.set_property,
                self.entity_description.property_key,
                int(value),
            )