"""DataUpdateCoordinator for Xiaomi Air Purifier."""
from __future__ import annotations

import math
import traceback
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_TOKEN,
    CONF_PASSWORD,
    CONF_USERNAME
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .xiaomi import XiaomiAirPurifierDevice, XiaomiAirPurifierProperty
from .const import (
    DOMAIN,
    LOGGER,
    CONF_COUNTRY,
    CONF_MAC,
    CONF_PREFER_CLOUD
)


class XiaomiAirPurifierDataUpdateCoordinator(DataUpdateCoordinator[XiaomiAirPurifierDevice]):
    """Class to manage fetching Xiaomi Air Purifier data from single endpoint."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry: ConfigEntry,
    ) -> None:
        """Initialize global Xiaomi Air Purifier data updater."""
        self._token = entry.data[CONF_TOKEN]
        self._host = entry.data[CONF_HOST]
        self._entry = entry
        self._available = False

        self.device = XiaomiAirPurifierDevice(
            entry.data[CONF_NAME],
            self._host,
            self._token,
            entry.data.get(CONF_MAC),
            entry.data.get(CONF_USERNAME),
            entry.data.get(CONF_PASSWORD),
            entry.data.get(CONF_COUNTRY),
            entry.options.get(CONF_PREFER_CLOUD, False),
        )        
     
        self.device.listen(self.async_set_updated_data)
        self.device.listen_error(self.async_set_update_error)

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
        )
   
    async def _async_update_data(self) -> XiaomiAirPurifierDevice:
        """Handle device update. This function is only called once when the integration is added to Home Assistant."""
        try:
            await self.hass.async_add_executor_job(self.device.update)
            self.device.schedule_update()
            self.async_set_updated_data()
            return self.device
        except Exception as ex:
            LOGGER.error("Update failed: %s", traceback.format_exc())
            raise UpdateFailed(ex) from ex

    @callback
    def async_set_updated_data(self, device=None) -> None:
        if self.device.token != self._token or self.device.host != self._host:
            data = self._entry.data.copy()
            self._host = self.device.host
            self._token = self.device.token
            data[CONF_HOST] = self._host
            data[CONF_TOKEN] = self._token
            self.hass.config_entries.async_update_entry(self._entry, data=data)

        self._available = self.device.available

        super().async_set_updated_data(self.device)

    @callback
    def async_set_update_error(self, ex) -> None:
        if self._available:
            self._available = self.device.available
            super().async_set_update_error(ex)
