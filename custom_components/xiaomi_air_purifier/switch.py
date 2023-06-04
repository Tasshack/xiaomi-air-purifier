"""Support for Xiaomi Air Purifier switches."""
from __future__ import annotations

from typing import Any
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

from .coordinator import XiaomiAirPurifierDataUpdateCoordinator
from .entity import XiaomiAirPurifierEntity, XiaomiAirPurifierEntityDescription
from .xiaomi import XiaomiAirPurifierProperty


@dataclass
class XiaomiAirPurifierSwitchEntityDescription(
    XiaomiAirPurifierEntityDescription, SwitchEntityDescription
):
    """Describes Xiaomi Air Purifier Switch entity."""

    set_fn: Callable[[object, int]] = None


SWITCHES: tuple[XiaomiAirPurifierSwitchEntityDescription, ...] = (
    XiaomiAirPurifierSwitchEntityDescription(
        property_key=XiaomiAirPurifierProperty.IONIZER,
        icon_fn=lambda value, device: "mdi:minus-circle-off-outline"
        if value == 0
        else "mdi:minus-circle-multiple-outline",
        entity_category=EntityCategory.CONFIG,
    ),
    XiaomiAirPurifierSwitchEntityDescription(
        property_key=XiaomiAirPurifierProperty.CHILD_LOCK,
        icon_fn=lambda value, device: "mdi:lock-off" if value == 0 else "mdi:lock",
        entity_category=EntityCategory.CONFIG,
    ),
    XiaomiAirPurifierSwitchEntityDescription(
        property_key=XiaomiAirPurifierProperty.SOUND,
        icon_fn=lambda value, device: "mdi:volume-off"
        if value == 0
        else "mdi:volume-high",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaomi Air Purifier switch based on a config entry."""
    coordinator: XiaomiAirPurifierDataUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]
    async_add_entities(
        XiaomiAirPurifierSwitchEntity(coordinator, description)
        for description in SWITCHES
        if description.exists_fn(description, coordinator.device)
    )


class XiaomiAirPurifierSwitchEntity(XiaomiAirPurifierEntity, SwitchEntity):
    """Defines a Xiaomi Air Purifier Switch entity."""

    entity_description: XiaomiAirPurifierSwitchEntityDescription

    def __init__(
        self,
        coordinator: XiaomiAirPurifierDataUpdateCoordinator,
        description: XiaomiAirPurifierSwitchEntityDescription,
    ) -> None:
        """Initialize a Xiaomi Air Purifier switch entity."""
        super().__init__(coordinator, description)
        self._attr_is_on = bool(self.native_value)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = bool(self.native_value)
        super()._handle_coordinator_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the Xiaomi Air Purifier sync receive switch."""
        await self.async_set_state(0)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the Xiaomi Air Purifier sync receive switch."""
        await self.async_set_state(1)

    async def async_set_state(self, state) -> None:
        """Turn on or off the Xiaomi Air Purifier sync receive switch."""
        if not self.available:
            raise HomeAssistantError("Entity unavailable")

        if self.entity_description.format_fn is not None:
            value = self.entity_description.format_fn(state, self.device)

        value = bool(state)
        if self.entity_description.property_key is not None:
            await self._try_command(
                "Unable to call: %s",
                self.device.set_property,
                self.entity_description.property_key,
                value,
            )
        elif self.entity_description.set_fn is not None:
            await self._try_command(
                "Unable to call: %s", self.entity_description.set_fn, self.device, value
            )
