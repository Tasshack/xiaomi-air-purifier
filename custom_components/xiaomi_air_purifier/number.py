"""Support for Xiaomi Air Purifier numbers."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.const import PERCENTAGE
from .const import DOMAIN, FAN_LEVEL_TO_ICON, ATTR_VALUE

from .coordinator import XiaomiAirPurifierDataUpdateCoordinator
from .entity import XiaomiAirPurifierEntity, XiaomiAirPurifierEntityDescription
from .xiaomi import XiaomiAirPurifierAction, XiaomiAirPurifierProperty


@dataclass
class XiaomiAirPurifierNumberEntityDescription(
    XiaomiAirPurifierEntityDescription, NumberEntityDescription
):
    """Describes Xiaomi Air Purifier Number entity."""

    set_fn: Callable[[object, str]] = None
    mode: NumberMode = NumberMode.AUTO
    post_action: XiaomiAirPurifierAction = None


NUMBERS: tuple[XiaomiAirPurifierNumberEntityDescription, ...] = (
    XiaomiAirPurifierNumberEntityDescription(
        property_key=XiaomiAirPurifierProperty.SPEED,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        icon="mdi:weather-windy",
        entity_category=None,
        set_fn=lambda device, value: device.set_speed_percent(value),
        value_fn=lambda value, device: device.status.speed_percent,
        attrs_fn=lambda device: { ATTR_VALUE: device.status.speed },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaomi Air Purifier number based on a config entry."""
    coordinator: XiaomiAirPurifierDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        XiaomiAirPurifierNumberEntity(coordinator, description)
        for description in NUMBERS
        if description.exists_fn(description, coordinator.device)
    )


class XiaomiAirPurifierNumberEntity(XiaomiAirPurifierEntity, NumberEntity):
    """Defines a Xiaomi Air Purifier number."""

    def __init__(
        self,
        coordinator: XiaomiAirPurifierDataUpdateCoordinator,
        description: XiaomiAirPurifierNumberEntityDescription,
    ) -> None:
        """Initialize Xiaomi Air Purifier ."""
        super().__init__(coordinator, description)
        self._attr_mode = description.mode
        self._attr_native_value = super().native_value

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = super().native_value
        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        """Set the Xiaomi Air Purifier number value."""
        if not self.available:
            raise HomeAssistantError("Entity unavailable")

        value = int(value)
        if self.entity_description.format_fn is not None:
            value = self.entity_description.format_fn(value, self.device)

        if value is None:
            raise HomeAssistantError("Invalid value")

        if self.entity_description.set_fn is not None:
            await self._try_command(
                "Unable to call %s",
                self.entity_description.set_fn,
                self.device,
                value,
            )
        elif self.entity_description.property_key is not None:
            if await self._try_command(
                "Unable to call %s",
                self.device.set_property,
                self.entity_description.property_key,
                value,
            ):
                if self.entity_description.post_action is not None:
                    await self._try_command(
                        "Unable to call %s",
                        self.device.call_action,
                        self.entity_description.post_action,
                    )

    @property
    def native_value(self) -> int | None:
        """Return the current Xiaomi Air Purifier number value."""
        return self._attr_native_value
