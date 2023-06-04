from typing import Final
from .types import (
    XiaomiAirPurifierProperty,
    XiaomiAirPurifierAction,
    XiaomiAirPurifierFault,
    XiaomiAirPurifierDoorStatus,
    XiaomiAirPurifierRebootReason,
    XiaomiAirPurifierCountryCode,
    XiaomiAirPurifierAirQuality,
    XiaomiAirPurifierMode,
    XiaomiAirPurifierFanLevel,
    XiaomiAirPurifierScreenBrightness,
    XiaomiAirPurifierTemperatureUnit,
    XiaomiAirPurifierCoverage,
)

STATE_UNKNOWN: Final = "unknown"

FAULT_TO_NAME: Final = {
    XiaomiAirPurifierFault.UNKNOWN: STATE_UNKNOWN,
    XiaomiAirPurifierFault.NO_FAULT: "no_fault",
    XiaomiAirPurifierFault.PM_SENSOR: "pm_sensor",
    XiaomiAirPurifierFault.TEMP_SENSOR: "temperature_sensor",
    XiaomiAirPurifierFault.HUMIDITY_SENSOR: "humidity_sensor",
    XiaomiAirPurifierFault.NO_FILTER: "no_filter",
}

DOOR_STATUS_TO_NAME: Final = {
    XiaomiAirPurifierDoorStatus.UNKNOWN: STATE_UNKNOWN,
    XiaomiAirPurifierDoorStatus.CLOSED: "closed",
    XiaomiAirPurifierDoorStatus.OPEN: "open"
}

REBOOT_REASON_TO_NAME: Final = {
    XiaomiAirPurifierRebootReason.UNKNOWN: STATE_UNKNOWN,
    XiaomiAirPurifierRebootReason.BOOT: "boot",
    XiaomiAirPurifierRebootReason.REBOOT: "reboot",
    XiaomiAirPurifierRebootReason.UPDATE: "update",
    XiaomiAirPurifierRebootReason.WATCHDOG_TIMER: "watchdog_timer",
}

COUNTRY_CODE_TO_NAME: Final = {
    XiaomiAirPurifierCountryCode.US: "US",
    XiaomiAirPurifierCountryCode.EU: "EU",
    XiaomiAirPurifierCountryCode.KR: "KR",
    XiaomiAirPurifierCountryCode.TW: "TW",
    XiaomiAirPurifierCountryCode.TH: "TH",
    XiaomiAirPurifierCountryCode.UK: "UK",
    XiaomiAirPurifierCountryCode.IN: "IN",
}

AIR_QUALITY_TO_NAME: Final = {
    XiaomiAirPurifierAirQuality.UNKNOWN: STATE_UNKNOWN,
    XiaomiAirPurifierAirQuality.EXCELLENT: "excellent",
    XiaomiAirPurifierAirQuality.GOOD: "good",
    XiaomiAirPurifierAirQuality.MODERATE: "moderate",
    XiaomiAirPurifierAirQuality.POOR: "poor",
    XiaomiAirPurifierAirQuality.UNHEALTY: "unhealty",
    XiaomiAirPurifierAirQuality.HAZARDOUS: "hazardous",
}

MODE_TO_NAME: Final = {
    XiaomiAirPurifierMode.AUTO: "auto",
    XiaomiAirPurifierMode.SLEEP: "sleep",
    XiaomiAirPurifierMode.FAVORITE: "favorite",
    XiaomiAirPurifierMode.MANUAL: "manual",
}

FAN_LEVEL_TO_NAME: Final = {
    XiaomiAirPurifierFanLevel.HIGH: "high",
    XiaomiAirPurifierFanLevel.MEDIUM: "medium",
    XiaomiAirPurifierFanLevel.LOW: "low",
}

SCREEN_BRIGHTNESS_TO_NAME: Final = {
    XiaomiAirPurifierScreenBrightness.OFF: "off",
    XiaomiAirPurifierScreenBrightness.DIM: "dim",
    XiaomiAirPurifierScreenBrightness.BRIGHT: "bright",
}

TEMPERATURE_UNIT_TO_NAME: Final = {
    XiaomiAirPurifierTemperatureUnit.CELCIUS: "celcius",
    XiaomiAirPurifierTemperatureUnit.FAHRENHEIT: "fahrenheit",
}

COVERAGE_TO_NAME: Final = {
    XiaomiAirPurifierCoverage.FIVE_TO_NINE: "five_to_nine",
    XiaomiAirPurifierCoverage.SEVEN_TO_THIRTHEEN: "seven_to_thirtheen",
    XiaomiAirPurifierCoverage.ELEVEN_TO_NINETEEN: "eleven_to_nineteen",
    XiaomiAirPurifierCoverage.THIRTHEEN_TO_TWENTY_TWO: "thirtheen_to_twenty_two",
    XiaomiAirPurifierCoverage.SEVENTEEN_TO_TWENTY_EIGHT: "seventeen_to_twenty_eight",
    XiaomiAirPurifierCoverage.NINETEEN_TO_THIRTY_THREE: "nineteen_to_thirty_three",
    XiaomiAirPurifierCoverage.TWENTY_TO_THIRTY_FOUR: "twenty_to_thirty_four",
    XiaomiAirPurifierCoverage.TWENTY_ONE_TO_THIRTY_SIX: "twenty_one_to_thirty_six",
    XiaomiAirPurifierCoverage.TWENTY_THREE_TO_THIRTY_NINE: "twenty_three_to_thirty_nine",
    XiaomiAirPurifierCoverage.TWENTY_FOUR_TO_FOURTY: "twenty_four_to_fourty",
    XiaomiAirPurifierCoverage.TWENTY_SIX_TO_FOURTY_FOUR: "twenty_six_to_fourty_four",
    XiaomiAirPurifierCoverage.TWENTY_EIGHT_TO_FOURTY_EIGHT: "twenty_eight_to_fourty_eight",
    XiaomiAirPurifierCoverage.MANUAL: "manual",
}


PROPERTY_TO_NAME: Final = {
    XiaomiAirPurifierProperty.POWER: ["power", "Power"],
    XiaomiAirPurifierProperty.FAULT: ["fault", "Fault"],
    XiaomiAirPurifierProperty.MODE: ["mode", "Mode"],
    XiaomiAirPurifierProperty.FAN_LEVEL: ["fan_level", "Fan Level"],
    XiaomiAirPurifierProperty.IONIZER: ["ionizer", "Ionizer"],
    XiaomiAirPurifierProperty.HUMIDITY: ["humidity", "Humidity"],
    XiaomiAirPurifierProperty.PM2_5: ["pm2_5", "PM2.5"],
    XiaomiAirPurifierProperty.TEMPERATURE: ["temperature", "Temprature"],
    XiaomiAirPurifierProperty.FILTER_LIFE_LEFT: ["filter_life_left", "Filter Life Left"],
    XiaomiAirPurifierProperty.FILTER_USED_TIME: ["filter_used_time", "Filter Used Time"],
    XiaomiAirPurifierProperty.FILTER_LEFT_TIME: ["filter_left_time", "Filter Left Time"],
    XiaomiAirPurifierProperty.SOUND: ["sound", "Sound"],
    XiaomiAirPurifierProperty.CHILD_LOCK: ["child_lock", "Child Lock"],
    XiaomiAirPurifierProperty.FAN_SPEED: ["fan_speed", "Fan Speed"],
    XiaomiAirPurifierProperty.SPEED: ["speed", "Speed"],
    XiaomiAirPurifierProperty.FAN_SET_SPEED: ["fan_set_speed", "Fan Set Speed"],
    XiaomiAirPurifierProperty.COVERAGE: ["coverage", "Coverage"],
    XiaomiAirPurifierProperty.DOOR_STATUS: ["door_status", "Door Status"],
    XiaomiAirPurifierProperty.REBOOT_REASON: ["reboot_reason", "Reboot Reason"],
    XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL: ["fan_level", "Fan Level"],
    XiaomiAirPurifierProperty.COUNTRY_CODE: ["country_code", "Country Code"],
    XiaomiAirPurifierProperty.IIC_ERROR_COUNT: ["iic_error_count", "IIC Error Count"],
    XiaomiAirPurifierProperty.FILTER_USE: ["filter_use", "Filter Use"],
    XiaomiAirPurifierProperty.CLEANED_AREA: ["cleaned_area", "Cleaned Area"],
    XiaomiAirPurifierProperty.AVERAGE_PM2_5: ["average_pm2_5", "Average PM2.5"],
    XiaomiAirPurifierProperty.AIR_QUALITY: ["air_quality", "Air Quality"],
    XiaomiAirPurifierProperty.AIR_QUALITY_HEARTBEAT: ["air_quality_heartbeat", "Air Quality Heartbeat"],
    XiaomiAirPurifierProperty.RFID_TAG: ["rfid_tag", "RFID Tag"],
    XiaomiAirPurifierProperty.RFID_MANUFACTURER: ["rfid_manufacturer", "RFID Manufacturer"],
    XiaomiAirPurifierProperty.RFID_PRODUCT: ["rfid_product", "RFID Product"],
    XiaomiAirPurifierProperty.RFID_TIME: ["rfid_time", "RFID Time"],
    XiaomiAirPurifierProperty.RFID_SERIAL: ["rfid_serial", "RFID Serial"],
    XiaomiAirPurifierProperty.SCREEN_BRIGHTNESS: ["screen_brightness", "Screen Brightness"],
    XiaomiAirPurifierProperty.TEMPERATURE_UNIT: ["temperature_unit", "Temperature Unit"],
}

ACTION_TO_NAME: Final = {
    XiaomiAirPurifierAction.TOGGLE_POWER: ["toggle_power", "Toggle Power"],
    XiaomiAirPurifierAction.RESET_FILTER: ["reset_filter", "Reset Filter"],
    XiaomiAirPurifierAction.TOGGLE_MODE: ["toggle_mode", "Toggle Mode"],
    XiaomiAirPurifierAction.TOGGLE_POWER: ["toggle_fan_level", "Toggle Fan Level"],
}