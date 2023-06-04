from __future__ import annotations

import math
from typing import Any, Dict, Final, List, Optional
from enum import IntEnum, Enum
from dataclasses import dataclass, field
from datetime import datetime

class XiaomiAirPurifierFault(IntEnum):
    """Xiaomi Air Purififer fault"""

    UNKNOWN = -1
    NO_FAULT = 0
    PM_SENSOR = 1
    TEMP_SENSOR = 2
    HUMIDITY_SENSOR = 3
    NO_FILTER = 4


class XiaomiAirPurifierDoorStatus(IntEnum):
    """Xiaomi Air Purififer door status"""

    UNKNOWN = -1
    CLOSED = 0
    OPEN = 1


class XiaomiAirPurifierRebootReason(IntEnum):
    """Xiaomi Air Purififer reboot reason"""

    UNKNOWN = -1
    BOOT = 0
    REBOOT = 1
    UPDATE = 2
    WATCHDOG_TIMER = 3


class XiaomiAirPurifierCountryCode(IntEnum):
    """Xiaomi Air Purififer country code"""

    UNKNOWN = -1
    US = 1
    EU = 2
    KR = 82
    TW = 886
    TH = 66
    UK = 44
    IN = 91


class XiaomiAirPurifierAirQuality(IntEnum):
    """Xiaomi Air Purififer air quality"""

    UNKNOWN = -1
    EXCELLENT = 0
    GOOD = 1
    MODERATE = 2
    POOR = 3
    UNHEALTY = 4
    HAZARDOUS = 5


class XiaomiAirPurifierMode(IntEnum):
    """Xiaomi Air Purififer mode"""

    AUTO = 0
    SLEEP = 1
    FAVORITE = 2
    MANUAL = 3


class XiaomiAirPurifierFanLevel(IntEnum):
    """Xiaomi Air Purififer fan level"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class XiaomiAirPurifierScreenBrightness(IntEnum):
    """Xiaomi Air Purififer screen brightness"""

    OFF = 0
    DIM = 1
    BRIGHT = 2


class XiaomiAirPurifierTemperatureUnit(IntEnum):
    """Xiaomi Air Purififer temperature unit"""

    CELCIUS = 1
    FAHRENHEIT = 2

class XiaomiAirPurifierCoverage(IntEnum):
    """Xiaomi Air Purififer coverage"""

    FIVE_TO_NINE = 0
    SEVEN_TO_THIRTHEEN = 1
    ELEVEN_TO_NINETEEN = 2
    THIRTHEEN_TO_TWENTY_TWO = 3
    SEVENTEEN_TO_TWENTY_EIGHT = 4
    NINETEEN_TO_THIRTY_THREE = 5
    TWENTY_TO_THIRTY_FOUR = 6
    TWENTY_ONE_TO_THIRTY_SIX = 7
    TWENTY_THREE_TO_THIRTY_NINE = 8
    TWENTY_FOUR_TO_FOURTY = 9
    TWENTY_SIX_TO_FOURTY_FOUR = 10
    TWENTY_EIGHT_TO_FOURTY_EIGHT = 11
    MANUAL = 12


class XiaomiAirPurifierProperty(IntEnum):
    """Xiaomi Air Purifier properties"""

    POWER = 0
    FAULT = 1
    MODE = 2
    FAN_LEVEL = 3
    IONIZER = 4
    HUMIDITY = 5
    PM2_5 = 6
    TEMPERATURE = 7
    FILTER_LIFE_LEFT = 8
    FILTER_USED_TIME = 9
    FILTER_LEFT_TIME = 10
    SOUND = 11
    CHILD_LOCK = 12
    FAN_SPEED = 13
    SPEED = 14
    FAN_SET_SPEED = 15
    COVERAGE = 16
    DOOR_STATUS = 17
    REBOOT_REASON = 18
    MANUAL_FAN_LEVEL = 19
    COUNTRY_CODE = 20
    IIC_ERROR_COUNT = 21
    FILTER_USE = 22
    CLEANED_AREA = 23
    AVERAGE_PM2_5 = 24
    AIR_QUALITY = 25
    AIR_QUALITY_HEARTBEAT = 26
    RFID_TAG = 27
    RFID_MANUFACTURER = 28
    RFID_PRODUCT = 29
    RFID_TIME = 30
    RFID_SERIAL = 31
    SCREEN_BRIGHTNESS = 32
    TEMPERATURE_UNIT = 33

class XiaomiAirPurifierAction(IntEnum):
    """Xiaomi Air Purifier actions"""

    TOGGLE_POWER = 1
    RESET_FILTER = 2
    TOGGLE_MODE = 3,
    TOGGLE_FAN_LEVEL = 4


# Xiaomi Air Purifier property mapping
XiaomiAirPurifierPropertyMapping = {
    XiaomiAirPurifierProperty.POWER: {"siid": 2, "piid": 1},
    XiaomiAirPurifierProperty.FAULT: {"siid": 2, "piid": 2},
    XiaomiAirPurifierProperty.MODE: {"siid": 2, "piid": 4},
    XiaomiAirPurifierProperty.FAN_LEVEL: {"siid": 2, "piid": 5},
    XiaomiAirPurifierProperty.IONIZER: {"siid": 2, "piid": 6},
    XiaomiAirPurifierProperty.HUMIDITY: {"siid": 3, "piid": 1},
    XiaomiAirPurifierProperty.PM2_5: {"siid": 3, "piid": 4},
    XiaomiAirPurifierProperty.TEMPERATURE: {"siid": 3, "piid": 7},
    XiaomiAirPurifierProperty.FILTER_LIFE_LEFT: {"siid": 4, "piid": 1},
    XiaomiAirPurifierProperty.FILTER_USED_TIME: {"siid": 4, "piid": 3},
    XiaomiAirPurifierProperty.FILTER_LEFT_TIME: {"siid": 4, "piid": 4},
    XiaomiAirPurifierProperty.SOUND: {"siid": 6, "piid": 1},
    XiaomiAirPurifierProperty.CHILD_LOCK: {"siid": 8, "piid": 1},
    XiaomiAirPurifierProperty.FAN_SPEED: {"siid": 9, "piid": 1},
    XiaomiAirPurifierProperty.SPEED: {"siid": 9, "piid": 2},
    XiaomiAirPurifierProperty.FAN_SET_SPEED: {"siid": 9, "piid": 4},
    XiaomiAirPurifierProperty.COVERAGE: {"siid": 9, "piid": 5},
    XiaomiAirPurifierProperty.DOOR_STATUS: {"siid": 9, "piid": 6},
    XiaomiAirPurifierProperty.REBOOT_REASON: {"siid": 9, "piid": 8},
    XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL: {"siid": 9, "piid": 9},
    XiaomiAirPurifierProperty.COUNTRY_CODE: {"siid": 9, "piid": 10},
    XiaomiAirPurifierProperty.IIC_ERROR_COUNT: {"siid": 9, "piid": 11},
    XiaomiAirPurifierProperty.FILTER_USE: {"siid": 10, "piid": 1},
    XiaomiAirPurifierProperty.CLEANED_AREA: {"siid": 11, "piid": 1},
    XiaomiAirPurifierProperty.AVERAGE_PM2_5: {"siid": 11, "piid": 2},
    XiaomiAirPurifierProperty.AIR_QUALITY: {"siid": 11, "piid": 3},
    XiaomiAirPurifierProperty.AIR_QUALITY_HEARTBEAT: {"siid": 11, "piid": 4},
    XiaomiAirPurifierProperty.RFID_TAG: {"siid": 12, "piid": 1},
    XiaomiAirPurifierProperty.RFID_MANUFACTURER: {"siid": 12, "piid": 2},
    XiaomiAirPurifierProperty.RFID_PRODUCT: {"siid": 12, "piid": 3},
    XiaomiAirPurifierProperty.RFID_TIME: {"siid": 12, "piid": 4},
    XiaomiAirPurifierProperty.RFID_SERIAL: {"siid": 12, "piid": 5},
    XiaomiAirPurifierProperty.SCREEN_BRIGHTNESS: {"siid": 13, "piid": 2},
    XiaomiAirPurifierProperty.TEMPERATURE_UNIT: {"siid": 14, "piid": 1},
}

# Xiaomi Air Purifier action mapping
XiaomiAirPurifierActionMapping = {
    XiaomiAirPurifierAction.TOGGLE_POWER: {"siid": 2, "aiid": 1},
    XiaomiAirPurifierAction.RESET_FILTER: {"siid": 4, "aiid": 1},
    XiaomiAirPurifierAction.TOGGLE_MODE: {"siid": 9, "aiid": 1},
    XiaomiAirPurifierAction.TOGGLE_FAN_LEVEL: {"siid": 9, "aiid": 2},
}

PROPERTY_AVAILABILITY: Final = {
    XiaomiAirPurifierProperty.SPEED: lambda device: device.status.power and device.status.favorite_mode and device.status.manual_coverage,
    XiaomiAirPurifierProperty.COVERAGE: lambda device: device.status.power and device.status.favorite_mode,
    XiaomiAirPurifierProperty.MODE: lambda device: device.status.power,
    XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL: lambda device: device.status.power and device.status.manual_mode,
    XiaomiAirPurifierProperty.FAN_LEVEL: lambda device: device.status.power,
    XiaomiAirPurifierProperty.FAN_SPEED: lambda device: device.status.power,
    XiaomiAirPurifierProperty.FAN_SET_SPEED: lambda device: device.status.power,
}

ACTION_AVAILABILITY: Final = {
    XiaomiAirPurifierAction.RESET_FILTER: lambda device: bool(device.status.filter_life_left < 100),
}


def PIID(property: XiaomiAirPurifierProperty, mapping=XiaomiAirPurifierPropertyMapping) -> int | None:
    if property in mapping:
        return mapping[property]["piid"]


def DIID(property: XiaomiAirPurifierProperty, mapping=XiaomiAirPurifierPropertyMapping) -> str | None:
    if property in mapping:
        return f'{mapping[property]["siid"]}.{mapping[property]["piid"]}'