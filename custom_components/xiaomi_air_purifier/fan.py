from __future__ import annotations

import voluptuous as vol
from typing import Any, Final

from .coordinator import XiaomiAirPurifierDataUpdateCoordinator
from .entity import XiaomiAirPurifierEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE, STATE_ON, STATE_OFF
from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature
)

from .const import (
    DOMAIN,   
    SERVICE_RESET_FILTER,
    SERVICE_TOGGLE_POWER,
    SERVICE_TOGGLE_MODE,
    SERVICE_TOGGLE_FAN_LEVEL
)

from .xiaomi import XiaomiAirPurifierMode, XiaomiAirPurifierFanLevel

FAN_LEVEL_TO_FAN_SPEED: Final = {
    XiaomiAirPurifierFanLevel.HIGH: "High",
    XiaomiAirPurifierFanLevel.MEDIUM: "Medium",
    XiaomiAirPurifierFanLevel.LOW: "Low",
}

MODE_TO_PRESET: Final = {
    XiaomiAirPurifierMode.AUTO: "Auto",
    XiaomiAirPurifierMode.SLEEP: "Sleep",
    XiaomiAirPurifierMode.FAVORITE: "Favorite",
    XiaomiAirPurifierMode.MANUAL: "Manual",
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Xiaomi Air Purifier based on a config entry."""
    coordinator: XiaomiAirPurifierDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_RESET_FILTER,
        {},
        XiaomiAirPurifier.async_reset_filter.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_TOGGLE_POWER,
        {},
        XiaomiAirPurifier.async_toggle_power.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_TOGGLE_MODE,
        {},
        XiaomiAirPurifier.async_toggle_mode.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_TOGGLE_FAN_LEVEL,
        {},
        XiaomiAirPurifier.async_toggle_fan_level.__name__,
    )


    async_add_entities([XiaomiAirPurifier(coordinator)])


class XiaomiAirPurifier(XiaomiAirPurifierEntity, FanEntity):
    """Representation of a Xiaomi Air Purifier cleaner robot."""

    def __init__(self, coordinator: XiaomiAirPurifierDataUpdateCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)


        
        self._attr_device_class = DOMAIN
        self._attr_name = coordinator.device.name
        self._attr_unique_id = f"{coordinator.device.mac}_" + DOMAIN
        self._set_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._set_attrs()
        self.async_write_ha_state()

    def _set_attrs(self):
        if self.device.status.has_error:
            self._attr_icon = "mdi:fan-alert"
        elif not self.device.status.power:
            self._attr_icon = "mdi:air-purifier-off"    
        elif self.device.status.auto_mode:
            self._attr_supported_features = FanEntityFeature.PRESET_MODE
            self._attr_icon = "mdi:fan-auto"
        elif self.device.status.sleep_mode:
            self._attr_icon = "mdi:sleep"
        elif self.device.status.fan_level == XiaomiAirPurifierFanLevel.LOW:
            self._attr_icon = "mdi:fan-speed-1"
        elif self.device.status.fan_level == XiaomiAirPurifierFanLevel.MEDIUM:
            self._attr_icon = "mdi:fan-speed-2"
        elif self.device.status.fan_level == XiaomiAirPurifierFanLevel.HIGH:
            self._attr_icon = "mdi:fan-speed-3"
        else:
            self._attr_icon = "mdi:fan"

        if self.device.status.sleep_mode or self.device.status.auto_mode:
            self._attr_supported_features = FanEntityFeature.PRESET_MODE
            self._speed_count = 1
        else:            
            self._attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
            self._speed_count = self.device.status.speed_count

        self._percentage = self.device.status.percentage
        self._preset_mode = self.device.status.mode_name.replace("_", "").title()
        self._preset_modes = list(MODE_TO_PRESET.values())
        self._state = self.device.status.power
        self._attr_extra_state_attributes = self.device.status.attributes

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        return self._state
        
    @property
    def percentage(self) -> int | None:
        """Return the current percentage based speed."""
        return self._percentage
    
    @property
    def speed_count(self) -> int:
        """Return the number of speeds of the fan supported."""
        return self._speed_count

    @property
    def preset_modes(self):
        """Get the list of available preset modes."""
        return self._preset_modes

    @property
    def preset_mode(self):
        """Get the current preset mode."""
        return self._preset_mode

    @property
    def supported_features(self) -> int:
        """Flag vacuum cleaner features that are supported."""
        return self._attr_supported_features

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the extra state attributes of the entity."""
        return self._attr_extra_state_attributes

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._attr_available and self.device.device_connected
    
    async def async_set_percentage(self, percentage) -> None:
        """Set the speed of the fan, as a percentage."""
        if percentage == 0:
            await self.async_turn_off()
        else:
            await self._try_command(
                "Unable to call: %s",
                self.device.set_percentage,
                percentage,
            )

    async def async_turn_on(
        self,
        speed: str = None,
        percentage: int = None,
        preset_mode: str = None,
        **kwargs,
    ) -> None:
        """Turn the device on."""
        if preset_mode:
            await self._try_command(
                "Unable to call: %s",
                self.device.set_mode,
                XiaomiAirPurifierMode[preset_mode.upper()],
            )
        else:
            await self._try_command(
                "Unable to call: %s",
                self.device.turn_on,
            )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        await self._try_command(
            "Unable to call: %s",
            self.device.turn_off
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        await self._try_command(
            "Unable to call: %s",
            self.device.set_mode,
            XiaomiAirPurifierMode[preset_mode.upper()],
        )

    async def async_reset_filter(self):
        """Reset the filter lifetime and usage."""
        await self._try_command(
            "Unable to call: %s",
            self._device.reset_filter,
        )

    async def async_toggle_power(self):
        await self._try_command(
            "Unable to call: %s",
            self._device.toggle_power,
        )

    async def async_toggle_mode(self):
        await self._try_command(
            "Unable to call: %s",
            self._device.toggle_mode,
        )

    async def async_toggle_fan_level(self):
        await self._try_command(
            "Unable to call: %s",
            self._device.toggle_fan_level,
        )