import logging
from typing import Final

DOMAIN = "xiaomi_air_purifier"
LOGGER = logging.getLogger(__package__)

UNIT_HOURS: Final = "hours"
UNIT_DAYS: Final = "days"
UNIT_AREA: Final = "m³"

CONF_NOTIFY: Final = "notify"
CONF_COUNTRY: Final = "country"
CONF_MANUAL: Final = "manual"
CONF_MAC: Final = "mac"
CONF_PREFER_CLOUD: Final = "prefer_cloud"

SERVICE_RESET_FILTER = "fan_reset_filter"
SERVICE_TOGGLE_POWER = "fan_toggle_power"
SERVICE_TOGGLE_MODE = "fan_toggle_mode"
SERVICE_TOGGLE_FAN_LEVEL = "fan_toggle_fan_level"
SERVICE_SELECT_NEXT = "select_select_next"
SERVICE_SELECT_PREVIOUS = "select_select_previous"
SERVICE_SELECT_FIRST = "select_select_first"
SERVICE_SELECT_LAST = "select_select_last"

ATTR_VALUE = "value"
INPUT_CYCLE = "cycle"

FAN_LEVEL_TO_ICON = {
    1: "mdi:fan-speed-1",
    2: "mdi:fan-speed-2",
    3: "mdi:fan-speed-3",
}

NOTIFICATION: Final = { "information": "Information", "warning": "Warning", "error": "Error" }

NOTIFICATION_ID_WARNING: Final = "warning"
NOTIFICATION_ID_ERROR: Final = "error"
NOTIFICATION_ID_INFO: Final = "info"
NOTIFICATION_ID_2FA_LOGIN: Final = "2fa_login"

NOTIFICATION_2FA_LOGIN: Final = "### Additional authentication required.\nOpen following URL using device that has the same public IP, as your Home Assistant instance:\n"