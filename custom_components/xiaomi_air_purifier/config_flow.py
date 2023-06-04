"""Config flow for Xiaomi Air Purifier."""
from __future__ import annotations
from typing import Any, Final
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from collections.abc import Mapping
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_TOKEN,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.device_registry import format_mac
from homeassistant.components import persistent_notification
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)

from .xiaomi import XiaomiAirPurifierProtocol

from .const import (
    DOMAIN,
    CONF_NOTIFY,
    CONF_COUNTRY,
    CONF_MAC,
    CONF_PREFER_CLOUD,
    NOTIFICATION,
    NOTIFICATION_ID_2FA_LOGIN,
    NOTIFICATION_2FA_LOGIN,
    CONF_MANUAL
)

SUPPORTED_MODELS = [
    "zhimi.airp.mb5",   
    "zhimi.airp.mb5a", 
]

class XiaomiAirPurifierOptionsFlowHandler(OptionsFlow):
    """Handle Xiaomi Air Purifier options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize Xiaomi Air Purifier options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Xiaomi Air Purifier options."""
        errors = {}
        data = self.config_entry.data
        options = self.config_entry.options

        if user_input is not None:
            return self.async_create_entry(title="", data={**options, **user_input})
        
        notify = options[CONF_NOTIFY]
        if isinstance(notify, bool):
            if notify is True:
                notify = list(NOTIFICATION.keys())
            else:
                notify = []

        data_schema = vol.Schema(
            {vol.Required(CONF_NOTIFY, default=notify): cv.multi_select(NOTIFICATION)}
        )
        if data[CONF_USERNAME]:
            data_schema = data_schema.extend(
                {
                    vol.Required(CONF_PREFER_CLOUD, default=options.get(CONF_PREFER_CLOUD, False)): bool,
                }
            )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )


class XiaomiAirPurifierFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle config flow for an Xiaomi Air Purifier device."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self.entry: ConfigEntry | None = None
        self.mac: str | None = None
        self.model = None
        self.host: str | None = None
        self.token: str | None = None
        self.name: str | None = None
        self.username: str | None = None
        self.password: str | None = None
        self.country: str = "cn"
        self.device_id: int | None = None
        self.prefer_cloud: bool = False
        self.devices: dict[str, dict[str, Any]] = {}
        self.protocol: XiaomiAirPurifierProtocol | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> XiaomiAirPurifierOptionsFlowHandler:
        """Get the options flow for this handler."""
        return XiaomiAirPurifierOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        return await self.async_step_cloud()

    async def async_step_reauth(self, user_input: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an authentication error or missing cloud credentials."""
        self.name = user_input[CONF_NAME]
        self.host = user_input[CONF_HOST]
        self.token = user_input[CONF_TOKEN]
        self.username = user_input[CONF_USERNAME]
        self.password = user_input[CONF_PASSWORD]
        self.country = user_input[CONF_COUNTRY]
        self.prefer_cloud = user_input[CONF_PREFER_CLOUD]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is not None:
            return await self.async_step_cloud()
        return self.async_show_form(step_id="reauth_confirm")

    async def async_step_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Connect to a Xiaomi Air Purifier device."""
        errors: dict[str, str] = {}
        if len(self.token) == 32:
            try:
                if self.protocol is None:
                    self.protocol = XiaomiAirPurifierProtocol(self.host, self.token, self.username, self.password, self.country, self.prefer_cloud)                
                else:
                    self.protocol.set_credentials(self.host, self.token)

                if self.protocol.device_cloud:
                    self.protocol.device_cloud.device_id = self.device_id

                info = await self.hass.async_add_executor_job(self.protocol.connect, 5)
                if info:
                    self.mac = info["mac"]
                    self.model = info["model"]
            except:
                errors["base"] = "cannot_connect"

                if self.prefer_cloud and self.username and self.password:
                    return await self.async_step_cloud(errors=errors)
            else:
                if self.mac:
                    await self.async_set_unique_id(format_mac(self.mac))
                    self._abort_if_unique_id_configured(
                        updates={
                            CONF_HOST: self.host,
                            CONF_TOKEN: self.token,
                            CONF_MAC: self.mac,
                        }
                    )

                if self.model in SUPPORTED_MODELS:
                    if self.name is None:
                        self.name = self.model
                    return await self.async_step_options()
                else:
                    errors["base"] = "unsupported"
        else:
            errors["base"] = "wrong_token"

        return await self.async_step_manual(errors=errors)

    async def async_step_manual(
        self,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, Any] | None = {},
    ) -> FlowResult:
        """Handle manual configuration step."""

        if user_input is not None:
            self._async_abort_entries_match(user_input)

            self.host = user_input[CONF_HOST]
            self.token = user_input[CONF_TOKEN]
            self.mac = None
            return await self.async_step_connect()

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.host): str,
                    vol.Required(CONF_TOKEN, default=self.token): str,
                }
            ),
            errors=errors,
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None, errors: dict[str, Any] | None = {}
    ) -> FlowResult:
        """Configure a Xiaomi Air Purifier device through the Miio Cloud."""
        placeholders = {}
        if user_input is not None:            
            if user_input[CONF_MANUAL]:
                return await self.async_step_manual()
            
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)
            country = user_input.get(CONF_COUNTRY)

            if username and password and country:
                self.username = username
                self.password = password
                self.country = country
                self.prefer_cloud = user_input.get(CONF_PREFER_CLOUD, False)

                self.protocol = XiaomiAirPurifierProtocol(username=self.username, password=self.password, country=self.country, prefer_cloud=self.prefer_cloud)
                await self.hass.async_add_executor_job(self.protocol.cloud.login)

                if self.protocol.cloud.two_factor_url is not None:
                    errors["base"] = "2fa_required"
                    persistent_notification.create(
                        self.hass,
                        f"{NOTIFICATION_2FA_LOGIN}[{self.protocol.cloud.two_factor_url}]({self.protocol.cloud.two_factor_url})",
                        f'Login to Xiaomi Air Purifier: {self.username}',
                        f'{DOMAIN}_{NOTIFICATION_ID_2FA_LOGIN}',
                    )
                    placeholders = {'url': self.protocol.cloud.two_factor_url }
                elif self.protocol.cloud.logged_in is False:
                    errors["base"] = "login_error"
                elif self.protocol.cloud.logged_in:
                    persistent_notification.dismiss(self.hass, f'{DOMAIN}_{NOTIFICATION_ID_2FA_LOGIN}')

                    devices = await self.hass.async_add_executor_job(
                        self.protocol.cloud.get_devices
                    )
                    if devices:
                        found = list(
                            filter(
                                lambda d: not d.get("parent_id")
                                and str(d["model"]) in SUPPORTED_MODELS,                                
                                devices["result"]["list"],
                            )
                        )

                        self.devices = {}
                        for device in found:
                            name = device["name"]
                            model = device["model"]
                            list_name = f"{name} - {model}"
                            self.devices[list_name] = device

                        if self.host is not None:
                            for device in self.devices.values():
                                host = device.get("localip")
                                if host == self.host:
                                    self.extract_info(device)
                                    return await self.async_step_connect()

                        if self.devices:
                            if len(self.devices) == 1:
                                self.extract_info(
                                    list(self.devices.values())[0])
                                return await self.async_step_connect()
                            return await self.async_step_devices()

                    errors["base"] = "no_devices"
            else:
                errors["base"] = "credentials_incomplete"

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str,
                    vol.Optional(CONF_COUNTRY, default=self.country): vol.In(
                        ["cn", "de", "us", "ru", "tw", "sg", "in", "i2"]
                    ),
                    vol.Optional(CONF_PREFER_CLOUD, default=self.prefer_cloud): bool,
                    vol.Optional(CONF_MANUAL, default=False): bool,
                }
            ),
            description_placeholders=placeholders,
            errors=errors,
        )

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle multiple Xiaomi Air Purifier devices found."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.extract_info(self.devices[user_input["devices"]])
            return await self.async_step_connect()

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema(
                {vol.Required("devices"): vol.In(list(self.devices))}
            ),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Xiaomi Air Purifier options step."""
        errors = {}

        if user_input is not None:
            self.name = user_input[CONF_NAME]
            
            return self.async_create_entry(
                title=self.name,
                data={
                    CONF_NAME: self.name,
                    CONF_HOST: self.host,
                    CONF_TOKEN: self.token,
                    CONF_USERNAME: self.username,
                    CONF_PASSWORD: self.password,
                    CONF_COUNTRY: self.country,
                    CONF_MAC: self.mac,
                },
                options={
                    CONF_NOTIFY: user_input[CONF_NOTIFY],
                    CONF_PREFER_CLOUD: self.prefer_cloud,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=self.name): str,
                vol.Required(CONF_NOTIFY, default=list(NOTIFICATION.keys())): cv.multi_select(NOTIFICATION),
            }
        )

        return self.async_show_form(
            step_id="options", data_schema=data_schema, errors=errors
        )

    def extract_info(self, device_info: dict[str, Any]) -> None:
        """Extract the device info."""
        if self.host is None:
            self.host = device_info["localip"]
        if self.mac is None:
            self.mac = device_info["mac"]
        if self.model is None:
            self.model = device_info["model"]
        if self.name is None:
            self.name = device_info["name"]
        self.token = device_info["token"]
        self.device_id = device_info["did"]