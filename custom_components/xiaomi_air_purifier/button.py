"""Support for Xiaomi Air Purifier buttons."""
from __future__ import annotations

from typing import Any
from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

from .coordinator import XiaomiAirPurifierDataUpdateCoordinator
from .entity import XiaomiAirPurifierEntity, XiaomiAirPurifierEntityDescription
from .xiaomi import XiaomiAirPurifierAction


@dataclass
class XiaomiAirPurifierButtonEntityDescription(
    XiaomiAirPurifierEntityDescription, ButtonEntityDescription
):
    """Describes Xiaomi Air Purifier Button entity."""

    parameters_fn: Callable[[object], Any] = None
    action_fn: Callable[[object]] = None


BUTTONS: tuple[ButtonEntityDescription, ...] = (
       XiaomiAirPurifierButtonEntityDescription(
        action_key=XiaomiAirPurifierAction.RESET_FILTER,
        icon="mdi:air-filter",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda description, device: bool(
            XiaomiAirPurifierEntityDescription().exists_fn(description, device)
            and device.status.filter_life_left is not None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaomi Air Purifier Button based on a config entry."""
    coordinator: XiaomiAirPurifierDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        XiaomiAirPurifierButtonEntity(coordinator, description)
        for description in BUTTONS
        if description.exists_fn(description, coordinator.device)
    )


class XiaomiAirPurifierButtonEntity(XiaomiAirPurifierEntity, ButtonEntity):
    """Defines a Xiaomi Air Purifier Button entity."""

    def __init__(
        self,
        coordinator: XiaomiAirPurifierDataUpdateCoordinator,
        description: XiaomiAirPurifierButtonEntityDescription,
    ) -> None:
        """Initialize a Xiaomi Air Purifier Button entity."""
        super().__init__(coordinator, description)

    async def async_press(self, **kwargs: Any) -> None:
        """Press the button."""
        if not self.available:
            raise HomeAssistantError("Entity unavailable")

        parameters = None
        if self.entity_description.parameters_fn is not None:
            parameters = self.entity_description.parameters_fn(self.device)

        if self.entity_description.action_key is not None:
            await self._try_command(
                "Unable to call %s",
                self.device.call_action,
                self.entity_description.action_key,
                parameters,
            )
        elif self.entity_description.action_fn is not None:
            await self._try_command(
                "Unable to call %s",
                self.entity_description.action_fn,
                self.device,
            )
