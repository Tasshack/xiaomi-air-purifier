from __future__ import annotations
import logging
import math
import time
from threading import Timer
from typing import Any, Optional

from .const import PROPERTY_TO_NAME, FAULT_TO_NAME, DOOR_STATUS_TO_NAME, REBOOT_REASON_TO_NAME, COUNTRY_CODE_TO_NAME, AIR_QUALITY_TO_NAME, MODE_TO_NAME, COVERAGE_TO_NAME, FAN_LEVEL_TO_NAME, SCREEN_BRIGHTNESS_TO_NAME, TEMPERATURE_UNIT_TO_NAME, STATE_UNKNOWN
from .types import (
    XiaomiAirPurifierProperty,
    XiaomiAirPurifierPropertyMapping,
    XiaomiAirPurifierAction,
    XiaomiAirPurifierActionMapping,
    XiaomiAirPurifierFault,
    XiaomiAirPurifierDoorStatus,
    XiaomiAirPurifierRebootReason,
    XiaomiAirPurifierCountryCode,
    XiaomiAirPurifierAirQuality,
    XiaomiAirPurifierMode,
    XiaomiAirPurifierFanLevel,
    XiaomiAirPurifierScreenBrightness,
    XiaomiAirPurifierTemperatureUnit,
    XiaomiAirPurifierCoverage
)

from .exceptions import (
    DeviceUpdateFailedException,
    InvalidActionException,
    InvalidValueException,
)
from .protocol import XiaomiAirPurifierProtocol

_LOGGER = logging.getLogger(__name__)


class XiaomiAirPurifierDevice:
    """Support for Xiaomi Air Purifier"""

    property_mapping: dict[XiaomiAirPurifierProperty,
                           dict[str, int]] = XiaomiAirPurifierPropertyMapping
    action_mapping: dict[XiaomiAirPurifierAction,
                         dict[str, int]] = XiaomiAirPurifierActionMapping

    def __init__(
        self,
        name: str,
        host: str,
        token: str,
        mac: str = None,
        username: str = None,
        password: str = None,
        country: str = None,
        prefer_cloud: bool = False,
    ) -> None:
        # Used for easy filtering the device from cloud device list and generating unique ids
        self.mac: str = None
        self.token: str = None  # Local api token
        self.host: str = None  # IP address or host name of the device
        # Dictionary for storing the current property values
        self.data: dict[XiaomiAirPurifierProperty, Any] = {}
        self.available: bool = False  # Last update is successful or not

        self._update_running: bool = False  # Update is running
        # Device do not request properties that returned -1 as result. This property used for overriding that behavior at first connection
        self._ready: bool = False
        # Last settings properties requested time
        self._last_settings_request: float = 0
        self._last_consumable_request: float = 0
        self._last_telemetry_request: float = 0
        self._last_change: float = 0  # Last property change time
        self._last_update_failed: float = 0  # Last update failed time      
        self._update_fail_count: int = 0 # Update failed counter
        # Map Manager object. Only available when cloud connection is present
        self._update_callback = None  # External update callback for device
        self._error_callback = None  # External update failed callback
        # External update callbacks for specific device property
        self._property_update_callback = {}
        self._update_timer: Timer = None  # Update schedule timer
        # Used for requesting consumable properties after reset action otherwise they will only requested when cleaning completed
        self._consumable_reset: bool = False
        self._dirty_data: dict[XiaomiAirPurifierProperty, Any] = {}

        self._name = name
        self.mac = mac
        self.token = token
        self.host = host
        self.two_factor_url = None
        self.status = XiaomiAirPurifierDeviceStatus(self)

        self._protocol = XiaomiAirPurifierProtocol(self.host, self.token, username, password, country, prefer_cloud)

    @staticmethod
    def percentage_to_ranged_value(
        low_high_range: tuple[float, float], percentage: int
    ) -> float:
        offset = low_high_range[0] - 1
        return (low_high_range[1] - low_high_range[0] + 1) * percentage / 100 + offset
    
    @staticmethod
    def ranged_value_to_percentage(
        low_high_range: tuple[float, float], value: float
    ) -> int:
        offset = low_high_range[0] - 1
        return int(((value - offset) * 100) // (low_high_range[1] - low_high_range[0] + 1))

    def _request_properties(self, properties: list[XiaomiAirPurifierProperty] = None) -> bool:
        """Request properties from the device."""
        if not properties:
            properties = [prop for prop in XiaomiAirPurifierProperty]

        property_list = []
        for prop in properties:
            if prop in self.property_mapping:
                mapping = self.property_mapping[prop]
                # Do not include properties that are not exists on the device
                if "aiid" not in mapping and (
                    not self._ready or prop.value in self.data
                ):
                    property_list.append({"did": str(prop.value), **mapping})

        props = property_list.copy()
        results = []
        while props:
            result = self._protocol.get_properties(props[:15])
            if result is not None:
                results.extend(result)
                props[:] = props[15:]

        changed = False
        callbacks = []
        for prop in results:
            if prop["code"] == 0 and "value" in prop:
                did = int(prop["did"])
                value = prop["value"]
                
                if did in self._dirty_data:
                    if self._dirty_data[did] != value:
                        _LOGGER.info("Property %s Value Discarded: %s <- %s", XiaomiAirPurifierProperty(did).name, self._dirty_data[did], value)
                    del self._dirty_data[did]
                    continue

                if self.data.get(did, None) != value:
                    # Do not call external listener when map list and recovery map list properties changed
                    changed = True
                    current_value = self.data.get(did)
                    if current_value is not None:
                        if did != 25 and did != 15 and did != 13 and did != 6 and did != 7 and did != 24 and did != 23:
                            _LOGGER.info(
                                "Property %s Changed: %s -> %s", XiaomiAirPurifierProperty(did).name, current_value, value)
                    else:
                        _LOGGER.info(
                            "Property %s Added: %s", XiaomiAirPurifierProperty(did).name, value)
                    self.data[did] = value
                    if did in self._property_update_callback:
                        for callback in self._property_update_callback[did]:
                            callbacks.append([callback, current_value])
                            
        for callback in callbacks:
            callback[0](callback[1])

        if changed:
            self._last_change = time.time()
            if self._ready:
                self._property_changed()
        return changed

    def _update_property(self, prop: XiaomiAirPurifierProperty, value: Any, force = False) -> Any:
        """Update device property on memory and notify listeners."""
        if prop in self.property_mapping:
            current_value = self.get_property(prop)
            if current_value != value or force:          
                _LOGGER.debug(
                    "Update Property: %s: %s -> %s", prop, current_value, value
                )
                      
                self._dirty_data[prop.value] = value
                did = prop.value
                self.data[did] = value

                if did in self._property_update_callback:
                    for callback in self._property_update_callback[did]:
                        callback(current_value)

                self._property_changed()

                return current_value if current_value is not None else value
        return None
 
    def _property_changed(self) -> None:
        """Call external listener when a property changed"""
        if self._update_callback:
            _LOGGER.debug("Update Callback")
            self._update_callback()

    def _update_failed(self, ex) -> None:
        """Call external listener when update failed"""
        if self._error_callback:
            self._error_callback(ex)

    def _update_task(self) -> None:
        """Timer task for updating properties periodically"""
        self._update_timer = None
        
        try:
            self.update()
            self._update_fail_count = 0
            self._last_update_failed = None
        except Exception as ex:
            self._update_fail_count = self._update_fail_count + 1
            if self.available:
                self._last_update_failed = time.time()
                if self._update_fail_count <= 3:
                    _LOGGER.warning("Update failed, retrying %s: %s", self._update_fail_count, ex)
                else:
                    _LOGGER.debug("Update Failed: %s", ex)
                    self.available = False
                    self._update_failed(ex)
              
        self.schedule_update(self._update_interval)

    def connect_device(self) -> None:
        """Connect to the device api."""
        _LOGGER.info("Connecting to device")
        self.info = XiaomiAirPurifierDeviceInfo(self._protocol.connect())
        if self.mac is None:
            self.mac = self.info.mac_address
        _LOGGER.info("Connected to device: %s %s", self.info.model, self.info.firmware_version)
            
        self._last_settings_request = time.time()
        self._last_consumable_request = self._last_settings_request
        self._last_telemetry_request = self._last_settings_request
        self._dirty_data = {}
        self._request_properties()
        self._last_update_failed = None
        if not self.available:
            self.available = True
            if self._ready:
                self._property_changed()

        self._ready = True

    def connect_cloud(self) -> None:
        """Connect to the cloud api."""
        if self._protocol.cloud and not self._protocol.cloud.logged_in:
            self._protocol.cloud.login()            
            if self._protocol.cloud.logged_in is False:
                if self._protocol.cloud.two_factor_url:
                    self.two_factor_url = self._protocol.cloud.two_factor_url                    
                    self._property_changed()
                return
            elif self._protocol.cloud.logged_in:
                if self.two_factor_url:
                    self.two_factor_url = None
                    self._property_changed()

                self.token, self.host = self._protocol.cloud.get_info(
                    self.mac)
                self._protocol.set_credentials(
                    self.host, self.token, self.mac)

    def disconnect(self) -> None:
        """Disconnect from device and cancel timers"""
        _LOGGER.info("Disconnect")
        self.schedule_update(-1)

    def listen(self, callback, property: XiaomiAirPurifierProperty = None) -> None:
        """Set callback functions for external listeners"""
        if callback is None:
            self._update_callback = None
            self._property_update_callback = {}
            return

        if property is None:
            self._update_callback = callback
        else:
            if property.value not in self._property_update_callback:
                self._property_update_callback[property.value] = []
            self._property_update_callback[property.value].append(callback)

    def listen_error(self, callback) -> None:
        """Set error callback function for external listeners"""
        self._error_callback = callback

    def schedule_update(self, wait: float = None) -> None:
        """Schedule a device update for future"""
        if not wait:
            wait = self._update_interval

        if self._update_timer is not None:
            self._update_timer.cancel()
            del self._update_timer
            self._update_timer = None

        if wait >= 0:
            self._update_timer = Timer(wait, self._update_task)
            self._update_timer.start()

    def get_property(self, prop: XiaomiAirPurifierProperty) -> Any:
        """Get a device property from memory"""
        if prop is not None and prop.value in self.data:
            return self.data[prop.value]
        return None

    def set_property(self, prop: XiaomiAirPurifierProperty, value: Any, force = False) -> bool:
        """Sets property value using the existing property mapping and notify listeners
        Property must be set on memory first and notify its listeners because device does not return new value immediately."""
        
        self.schedule_update(10)
        current_value = self._update_property(prop, value, force)
        if current_value is not None:
            _LOGGER.debug(
                "Set Property: %s: %s -> %s", prop, current_value, value
            )
            self._last_change = time.time()
            self._last_settings_request = 0

            try:
                mapping = self.property_mapping[prop]
                retries = 0
                while retries < 2:
                    result = self._protocol.set_property(mapping["siid"], mapping["piid"], value)
                    if result and result[0]["code"] != 0:
                        retries = retries + 1
                        continue
                    break

                if result and result[0]["code"] != 0:
                    _LOGGER.error(
                        "Property not updated: %s: %s -> %s", prop, current_value, value
                    )
                    self._update_property(prop, current_value)
                    if prop.value in self._dirty_data:
                        del self._dirty_data[prop.value]

                # Schedule the update for getting the updated property value from the device
                # If property is actually updated nothing will happen otherwise it will return to previous value and notify its listeners. (Post optimistic approach)
                self.schedule_update(0.3)
                return True
            except Exception as ex:
                self._update_property(prop, current_value)
                if prop.value in self._dirty_data:
                    del self._dirty_data[prop.value]
                self.schedule_update(1)
                raise DeviceUpdateFailedException(
                    "Set property failed %s: %s", prop.name, ex) from None

        self.schedule_update(1)
        return False

    def update(self) -> None:
        """Get properties from the device."""
        _LOGGER.debug("Device update: %s", self._update_interval)

        if self._update_running:
            return

        if not self.cloud_connected:
            self.connect_cloud()

        if not self.device_connected:
            self.connect_device()

        if not self.device_connected:
            raise DeviceUpdateFailedException("Device cannot be reached")

        self._update_running = True

        # Read-only properties
        properties = [
            XiaomiAirPurifierProperty.FAULT,
            XiaomiAirPurifierProperty.FAN_LEVEL,
            XiaomiAirPurifierProperty.PM2_5,
            XiaomiAirPurifierProperty.DOOR_STATUS,
            XiaomiAirPurifierProperty.AIR_QUALITY,
        ]

        now = time.time()
        if self.status.power:
            # Only changed when device is active
            properties.extend([
                    XiaomiAirPurifierProperty.FAN_SPEED,
                    XiaomiAirPurifierProperty.FAN_SET_SPEED,
               ])

        if now - self._last_settings_request > 9:
            self._last_settings_request = now

            # Read/Write properties
            properties.extend(
                [
                    XiaomiAirPurifierProperty.POWER,
                    XiaomiAirPurifierProperty.MODE,
                    XiaomiAirPurifierProperty.SCREEN_BRIGHTNESS,
                    XiaomiAirPurifierProperty.TEMPERATURE_UNIT,
                    XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL,
                    XiaomiAirPurifierProperty.SOUND,
                    XiaomiAirPurifierProperty.CHILD_LOCK,
                    XiaomiAirPurifierProperty.SPEED,
                    XiaomiAirPurifierProperty.COVERAGE,
                    XiaomiAirPurifierProperty.IONIZER,
                ]
            )
        if now - self._last_telemetry_request > 30:
            self._last_telemetry_request = now

            # Read/Write properties
            properties.extend(
                [
                    XiaomiAirPurifierProperty.HUMIDITY,
                    XiaomiAirPurifierProperty.TEMPERATURE,
                    XiaomiAirPurifierProperty.AVERAGE_PM2_5,
                    XiaomiAirPurifierProperty.FILTER_USED_TIME,
                    XiaomiAirPurifierProperty.CLEANED_AREA,
                ]
            )

        if now - self._last_consumable_request > 119 or self._consumable_reset:
            self._last_consumable_request = now

            # Read/Write properties
            properties.extend(
                [
                    XiaomiAirPurifierProperty.FILTER_LIFE_LEFT,
                    XiaomiAirPurifierProperty.FILTER_LEFT_TIME,
                    XiaomiAirPurifierProperty.RFID_TAG,
                    XiaomiAirPurifierProperty.RFID_MANUFACTURER,
                    XiaomiAirPurifierProperty.RFID_PRODUCT,
                    XiaomiAirPurifierProperty.RFID_TIME,
                    XiaomiAirPurifierProperty.RFID_SERIAL,
                    XiaomiAirPurifierProperty.REBOOT_REASON,
                    #XiaomiAirPurifierProperty.COUNTRY_CODE,
                ]
            )

        try:
            self._request_properties(properties)
        except Exception as ex:
            self._update_running = False
            raise DeviceUpdateFailedException(ex) from None

        if self._consumable_reset:
            self._consumable_reset = False

        self._update_running = False
        

    def call_action(self, action: XiaomiAirPurifierAction, parameters: dict[str, Any] = None) -> dict[str, Any] | None:
        """Call an action."""
        if action not in self.action_mapping:
            raise InvalidActionException(
                f"Unable to find {action} in the action mapping"
            )

        mapping = self.action_mapping[action]
        if "siid" not in mapping or "aiid" not in mapping:
            raise InvalidActionException(
                f"{action} is not an action (missing siid or aiid)"
            )

        self.schedule_update(10)

        # Reset consumable on memory
        if action is XiaomiAirPurifierAction.RESET_FILTER:
            self._consumable_reset = True
            self._update_property(XiaomiAirPurifierProperty.FILTER_LIFE_LEFT, 100)        

        # Update listeners
        self._property_changed()
            
        try:
            result = self._protocol.action(
                mapping["siid"], mapping["aiid"], parameters)
            if result and result.get("code") != 0:
                result = None
        except Exception as ex:
            _LOGGER.error("Send action failed %s: %s", action.name, ex)
            self.schedule_update(1)
            return

        if result:
            _LOGGER.info("Send action %s", action.name)
            self._last_change = time.time()
            self._last_settings_request = 0

        # Schedule update for retrieving new properties after action sent
        self.schedule_update(3)
        return result

    def send_command(self, command: str, parameters: dict[str, Any]) -> dict[str, Any] | None:
        """Send a raw command to the device. This is mostly useful when trying out
        commands which are not implemented by a given device instance. (Not likely)"""

        if command == "" or parameters is None:
            raise InvalidActionException("Invalid Command: (%s).", command)

        self.schedule_update(10)
        self._protocol.send(command, parameters, 1)
        self.schedule_update(2)

    def turn_on(self) -> bool:
        """Turn on."""
        return self.set_property(XiaomiAirPurifierProperty.POWER, True)
    
    def turn_off(self) -> bool:
        """Turn off."""        
        if self.set_property(XiaomiAirPurifierProperty.POWER, False):            
            self._update_property(XiaomiAirPurifierProperty.FAN_SPEED, 0)
            return True
        return False

    def set_coverage(self, coverage) -> bool:
        if not self.status.power:
            self.turn_on()
        if int(coverage) == XiaomiAirPurifierCoverage.MANUAL.value:
            return self.set_speed_percent(self.status.speed_percent)
        result = self.set_property(XiaomiAirPurifierProperty.COVERAGE, int(coverage)) 
        if result:
            if self.status.mode != XiaomiAirPurifierMode.FAVORITE:
                self.set_mode(XiaomiAirPurifierMode.FAVORITE.value)
            elif coverage != XiaomiAirPurifierCoverage.MANUAL and self.status.mode == XiaomiAirPurifierMode.FAVORITE:
                self._request_properties([XiaomiAirPurifierProperty.SPEED, XiaomiAirPurifierProperty.FAN_SET_SPEED, XiaomiAirPurifierProperty.FAN_LEVEL])
        return result

    def set_fan_level(self, fan_level) -> bool:
        currentMode = self.status.mode
        if not self.status.power:
            self._update_property(XiaomiAirPurifierProperty.POWER, True)      
        self._update_property(XiaomiAirPurifierProperty.MODE, XiaomiAirPurifierMode.MANUAL.value)
        if currentMode == XiaomiAirPurifierMode.AUTO or currentMode == XiaomiAirPurifierMode.SLEEP:
            self._update_property(XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL, int(fan_level))
            return self.set_property(XiaomiAirPurifierProperty.FAN_LEVEL, int(fan_level), True)
        else:
            self._update_property(XiaomiAirPurifierProperty.FAN_LEVEL, int(fan_level))
            return self.set_property(XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL, int(fan_level), True)

    def set_speed_percent(self, percent) -> bool:
        min = 200
        max = 2000
        speed = ((max - min) * (percent / 100.0)) + min
        if self.status.mode == XiaomiAirPurifierMode.FAVORITE:
            self._update_property(XiaomiAirPurifierProperty.FAN_SET_SPEED, int(speed))
        self._update_property(XiaomiAirPurifierProperty.COVERAGE, XiaomiAirPurifierCoverage.MANUAL.value)
        if self.set_property(XiaomiAirPurifierProperty.SPEED, int(speed), True):
            if self.status.mode != XiaomiAirPurifierMode.FAVORITE:
                return self.set_mode(XiaomiAirPurifierMode.FAVORITE.value)
            return True
        return False

    def set_mode(self, mode: int) -> bool:
        """Set mode."""   
        if mode == XiaomiAirPurifierMode.SLEEP.value:
            self._update_property(XiaomiAirPurifierProperty.FAN_LEVEL, XiaomiAirPurifierFanLevel.LOW.value)
        elif mode == XiaomiAirPurifierMode.MANUAL.value:
            self._update_property(XiaomiAirPurifierProperty.FAN_LEVEL, self.status.manual_fan_level.value)          
        if self.set_property(XiaomiAirPurifierProperty.MODE, mode, True):
            if not self.status.power:
                self._update_property(XiaomiAirPurifierProperty.POWER, True)      
            if mode == XiaomiAirPurifierMode.AUTO.value or (self.status.coverage != XiaomiAirPurifierCoverage.MANUAL and mode == XiaomiAirPurifierMode.FAVORITE):
                self._request_properties([XiaomiAirPurifierProperty.SPEED, XiaomiAirPurifierProperty.FAN_LEVEL, XiaomiAirPurifierProperty.FAN_SET_SPEED])
            return True
        return False

    def set_percentage(self, percent) -> bool:
        """Set percentage of fan level."""
        if percent == 100 and self.status.mode == XiaomiAirPurifierMode.SLEEP:
            if not self.status.power:
                self.turn_on()
            return

        if self.status.mode == XiaomiAirPurifierMode.FAVORITE:
            if not self.status.power:
                self.turn_on()
            coverage = self.status.coverage
            if coverage != -1 and coverage != XiaomiAirPurifierCoverage.MANUAL:
                return self.set_coverage(math.ceil(self.percentage_to_ranged_value((1, 12), percent) - 1))
            return self.set_speed_percent(percent)
        return self.set_fan_level(math.ceil(self.percentage_to_ranged_value((1, 3), percent)))

    def reset_filter(self):
        return self.call_action(XiaomiAirPurifierAction.RESET_FILTER)

    def toggle_power(self):
        return self.call_action(XiaomiAirPurifierAction.TOGGLE_POWER)
    
    def toggle_mode(self):
        return self.call_action(XiaomiAirPurifierAction.TOGGLE_MODE)
    
    def toggle_fan_level(self):
        return self.call_action(XiaomiAirPurifierAction.TOGGLE_FAN_LEVEL)

    @property
    def _update_interval(self) -> float:
        """Dynamic update interval of the device for the timer."""
        now = time.time()
        if self._last_update_failed:
            return 5 if now - self._last_update_failed <= 60 else 10 if now - self._last_update_failed <= 300 else 30
        return 3 if self.status.power else 10

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._name

    @property
    def device_connected(self) -> bool:
        """Return connection status of the device."""
        return self._protocol.connected

    @property
    def cloud_connected(self) -> bool:
        """Return connection status of the device."""
        return (
            self._protocol.cloud
            and self._protocol.cloud.logged_in
            and self._protocol.cloud.connected
        )
        


class XiaomiAirPurifierDeviceStatus:
    """Helper class for device status and int enum type properties."""

    mode_list = {v: k for k, v in MODE_TO_NAME.items()}
    fan_level_list = {v: k for k, v in FAN_LEVEL_TO_NAME.items()}
    screen_brightness_list = {v: k for k, v in SCREEN_BRIGHTNESS_TO_NAME.items()}
    temperature_unit_list = {v: k for k, v in TEMPERATURE_UNIT_TO_NAME.items()}
    coverage_list = {v: k for k, v in COVERAGE_TO_NAME.items()}

    def __init__(self, device):
        self._device = device

    def _get_property(self, prop: XiaomiAirPurifierProperty) -> Any:
        """Helper function for accessing a property from device"""
        return self._device.get_property(prop)

    @property
    def _device_connected(self) -> bool:
        """Helper property for accessing device connection status"""
        return self._device.device_connected

    @property
    def power(self) -> bool:
        """Returns true when device is active."""
        return bool(self._get_property(XiaomiAirPurifierProperty.POWER))

    @property
    def mode(self) -> XiaomiAirPurifierMode:
        """Return mode of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.MODE)
        if value is not None and value in XiaomiAirPurifierMode._value2member_map_:
            return XiaomiAirPurifierMode(value)
        _LOGGER.debug("MODE not supported: %s", value)
        return -1

    @property
    def mode_name(self) -> str:
        """Return mode as string for translation."""
        return MODE_TO_NAME.get(self.mode, STATE_UNKNOWN)
        
    @property
    def coverage(self) -> XiaomiAirPurifierCoverage:
        """Return coverage of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.COVERAGE)
        if value is not None and value in XiaomiAirPurifierCoverage._value2member_map_:
            return XiaomiAirPurifierCoverage(value)
        _LOGGER.debug("COVERAGE not supported: %s", value)
        return -1

    @property
    def coverage_name(self) -> str:
        """Return coverage as string for translation."""
        return COVERAGE_TO_NAME.get(self.coverage, STATE_UNKNOWN)

    @property
    def fan_level(self) -> XiaomiAirPurifierFanLevel:
        """Return fan level of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.FAN_LEVEL)
        if value is not None and value in XiaomiAirPurifierFanLevel._value2member_map_:
            return XiaomiAirPurifierFanLevel(value)
        _LOGGER.debug("FAN_LEVEL not supported: %s", value)
        return -1

    @property
    def fan_level_name(self) -> str:
        """Return fan level as string for translation."""
        return FAN_LEVEL_TO_NAME.get(self.fan_level, STATE_UNKNOWN)    

    @property
    def manual_fan_level(self) -> XiaomiAirPurifierFanLevel:
        """Return manual fan level of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL)
        if value is not None and value in XiaomiAirPurifierFanLevel._value2member_map_:
            return XiaomiAirPurifierFanLevel(value)
        _LOGGER.debug("MANUAL_FAN_LEVEL not supported: %s", value)
        return -1

    @property
    def manual_fan_level_name(self) -> str:
        """Return manual fan level as string for translation."""
        return FAN_LEVEL_TO_NAME.get(self.manual_fan_level, STATE_UNKNOWN)    

    @property
    def screen_brightness(self) -> XiaomiAirPurifierScreenBrightness:
        """Return screen brightness of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.SCREEN_BRIGHTNESS)
        if value is not None and value in XiaomiAirPurifierScreenBrightness._value2member_map_:
            return XiaomiAirPurifierScreenBrightness(value)
        _LOGGER.debug("SCREEN_BRIGHTNESS not supported: %s", value)
        return -1

    @property
    def screen_brightness_name(self) -> str:
        """Return screen brightness as string for translation."""
        return SCREEN_BRIGHTNESS_TO_NAME.get(self.screen_brightness, STATE_UNKNOWN)   
    
    @property
    def air_quality(self) -> XiaomiAirPurifierAirQuality:
        """Return air quality of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.AIR_QUALITY)
        if value is not None and value in XiaomiAirPurifierAirQuality._value2member_map_:
            return XiaomiAirPurifierAirQuality(value)
        _LOGGER.debug("AIR_QUALITY not supported: %s", value)
        return XiaomiAirPurifierAirQuality.UNKNOWN

    @property
    def air_quality_name(self) -> str:
        """Return air quality as string for translation."""
        return AIR_QUALITY_TO_NAME.get(self.air_quality, STATE_UNKNOWN)
    
    @property
    def fault(self) -> XiaomiAirPurifierFault:
        """Return fault of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.FAULT)
        if value is not None and value in XiaomiAirPurifierFault._value2member_map_:
            return XiaomiAirPurifierFault(value)
        _LOGGER.debug("FAULT not supported: %s", value)
        return XiaomiAirPurifierFault.UNKNOWN

    @property
    def fault_name(self) -> str:
        """Return fault as string for translation."""
        return FAULT_TO_NAME.get(self.fault, STATE_UNKNOWN)
    
    @property
    def door_status(self) -> XiaomiAirPurifierDoorStatus:
        """Return door status of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.DOOR_STATUS)
        if value is not None and value in XiaomiAirPurifierDoorStatus._value2member_map_:
            return XiaomiAirPurifierDoorStatus(value)
        _LOGGER.debug("DOOR_STATUS not supported: %s", value)
        return XiaomiAirPurifierDoorStatus.UNKNOWN

    @property
    def door_status_name(self) -> str:
        """Return mode as string for translation."""
        return DOOR_STATUS_TO_NAME.get(self.door_status, STATE_UNKNOWN)

    @property
    def reboot_reason(self) -> XiaomiAirPurifierRebootReason:
        """Return reboot reason of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.REBOOT_REASON)
        if value is not None and value in XiaomiAirPurifierRebootReason._value2member_map_:
            return XiaomiAirPurifierRebootReason(value)
        _LOGGER.debug("REBOOT_REASON not supported: %s", value)
        return XiaomiAirPurifierRebootReason.UNKNOWN

    @property
    def reboot_reason_name(self) -> str:
        """Return reboot reason as string for translation."""
        return REBOOT_REASON_TO_NAME.get(self.reboot_reason, STATE_UNKNOWN)

    @property
    def temperature_unit(self) -> XiaomiAirPurifierTemperatureUnit:
        """Return temperature unit of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.TEMPERATURE_UNIT)
        if value is not None and value in XiaomiAirPurifierTemperatureUnit._value2member_map_:
            return XiaomiAirPurifierTemperatureUnit(value)
        _LOGGER.debug("TEMPERATURE_UNIT not supported: %s", value)
        return XiaomiAirPurifierTemperatureUnit.UNKNOWN

    @property
    def temperature_unit_name(self) -> str:
        """Return temperature unit as string for translation."""
        return TEMPERATURE_UNIT_TO_NAME.get(self.temperature_unit, STATE_UNKNOWN)

    @property
    def country_code(self) -> XiaomiAirPurifierCountryCode:
        """Return reboot reason of the device."""
        value = self._get_property(XiaomiAirPurifierProperty.COUNTRY_CODE)
        if value is not None and value in XiaomiAirPurifierCountryCode._value2member_map_:
            return XiaomiAirPurifierCountryCode(value)
        _LOGGER.debug("COUNTRY_CODE not supported: %s", value)
        return value

    @property
    def country_code_name(self) -> str:
        """Return reboot reason as string for translation."""
        return COUNTRY_CODE_TO_NAME.get(self.country_code, str(self.country_code))
    
    @property
    def filter_life_left(self) -> int:
        """Returns filter remaining life in percent."""
        return self._get_property(XiaomiAirPurifierProperty.FILTER_LIFE_LEFT)

    @property
    def has_error(self) -> bool:
        """Returns true when an error is present."""
        return bool(self.fault.value > 0)            
    
    @property
    def ionizer(self) -> bool:
        """Returns true when ionizer is enabled."""
        return bool(self._get_property(XiaomiAirPurifierProperty.IONIZER) == 1) 

    @property
    def temperature(self) -> float:
        return round(float(self._get_property(XiaomiAirPurifierProperty.TEMPERATURE)), 1)

    @property
    def speed(self):
        return self._get_property(XiaomiAirPurifierProperty.SPEED)

    @property
    def speed_count(self):
        if self.mode == XiaomiAirPurifierMode.FAVORITE:
            if self.coverage != XiaomiAirPurifierCoverage.MANUAL:
                return 12
            return 100
        elif self.mode == XiaomiAirPurifierMode.SLEEP:
            return 1
        return 3

    @property
    def speed_percent(self) -> int:
        min = 200
        max = 2000
        return int(100 * (self._get_property(XiaomiAirPurifierProperty.SPEED) - min) / (max - min))

    @property
    def percentage(self):        
        if not self.power:
            return None
        
        if self.mode == XiaomiAirPurifierMode.FAVORITE:
            coverage = self.coverage
            if coverage != -1 and coverage != XiaomiAirPurifierCoverage.MANUAL:
                return self._device.ranged_value_to_percentage((1, 12), coverage + 1)
            return self.speed_percent
        elif self.mode == XiaomiAirPurifierMode.SLEEP:            
            return 100
        else:
            level = self.manual_fan_level

        count = self.speed_count
        return (100.0 / count) * level

    @property
    def rfid(self):
        return {
            "serial": self._get_property(XiaomiAirPurifierProperty.RFID_TAG),
            "product": self._get_property(XiaomiAirPurifierProperty.RFID_PRODUCT),
            "manufacturer": self._get_property(XiaomiAirPurifierProperty.RFID_MANUFACTURER),
            "time": self._get_property(XiaomiAirPurifierProperty.RFID_TIME),
            }

    @property
    def manual_coverage(self) -> bool:
        return self.coverage == XiaomiAirPurifierCoverage.MANUAL

    @property
    def favorite_mode(self) -> bool:
        return self.mode == XiaomiAirPurifierMode.FAVORITE
    
    @property
    def sleep_mode(self) -> bool:
        return self.mode == XiaomiAirPurifierMode.SLEEP
    
    @property
    def auto_mode(self) -> bool:
        return self.mode == XiaomiAirPurifierMode.AUTO
    
    @property
    def manual_mode(self) -> bool:
        return self.mode == XiaomiAirPurifierMode.MANUAL

    @property
    def attributes(self) -> dict[str, Any] | None:
        """Return the attributes of the device."""
        properties = [
            XiaomiAirPurifierProperty.FAULT,
            XiaomiAirPurifierProperty.FAN_LEVEL,
            XiaomiAirPurifierProperty.SPEED,
            XiaomiAirPurifierProperty.COVERAGE,
            XiaomiAirPurifierProperty.REBOOT_REASON,
            XiaomiAirPurifierProperty.FILTER_LIFE_LEFT,
            XiaomiAirPurifierProperty.DOOR_STATUS,
            XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL,
            XiaomiAirPurifierProperty.COUNTRY_CODE,
            XiaomiAirPurifierProperty.PM2_5,
            XiaomiAirPurifierProperty.AVERAGE_PM2_5,
        ]

        attributes = {}
     
        for prop in properties:
            value = self._get_property(prop)
            if value is not None:
                prop_name = PROPERTY_TO_NAME.get(prop)
                if prop_name:
                    prop_name = prop_name[0]
                else:
                    prop_name = prop.name.lower()

                if prop is XiaomiAirPurifierProperty.FAULT:
                    value = self.fault_name.replace("_", " ").capitalize()
                elif prop is XiaomiAirPurifierProperty.FAN_LEVEL:
                    value = self.fan_level_name.replace("_", " ").capitalize()
                elif prop is XiaomiAirPurifierProperty.COVERAGE:
                    value = self.coverage.value
                elif prop is XiaomiAirPurifierProperty.REBOOT_REASON:
                    value = self.reboot_reason_name.replace("_", " ").capitalize()
                elif prop is XiaomiAirPurifierProperty.DOOR_STATUS:
                    value = bool(self.door_status.value)
                elif prop is XiaomiAirPurifierProperty.MANUAL_FAN_LEVEL:
                    value = self.manual_fan_level_name.replace("_", " ").capitalize()
                elif prop is XiaomiAirPurifierProperty.COUNTRY_CODE:
                    value = self.country_code_name.upper()

                attributes[prop_name] = value    

        return attributes


class XiaomiAirPurifierDeviceInfo:
    """Container of device information."""

    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return "%s v%s (%s) @ %s - token: %s" % (
            self.data["model"],
            self.data["fw_ver"],
            self.data["mac"],
            self.network_interface["localIp"],
            self.data["token"],
        )

    @property
    def network_interface(self) -> str:
        """Information about network configuration."""
        return self.data["netif"]

    @property
    def accesspoint(self) -> str:
        """Information about connected WLAN access point."""
        return self.data["ap"]

    @property
    def model(self) -> Optional[str]:
        """Model string if available."""
        if self.data["model"] is not None:
            return self.data["model"]
        return None

    @property
    def firmware_version(self) -> Optional[str]:
        """Firmware version if available."""
        if self.data["fw_ver"] is not None:
            return self.data["fw_ver"]
        return None

    @property
    def version(self) -> Optional[int]:
        """Firmware version number if firmware version available."""
        firmware_version = self.firmware_version
        if firmware_version is not None:
            firmware_version = firmware_version.split("_")
            if len(firmware_version) == 2:
                return int(firmware_version[1])
        return None

    @property
    def hardware_version(self) -> Optional[str]:
        """Hardware version if available."""
        if self.data["hw_ver"] is not None:
            return self.data["hw_ver"]
        return None

    @property
    def mac_address(self) -> Optional[str]:
        """MAC address if available."""
        if self.data["mac"] is not None:
            return self.data["mac"]
        return None

    @property
    def manufacturer(self) -> str:
        """Manufacturer name."""
        return "Xiaomi"

    @property
    def raw(self) -> dict[str, Any]:
        """Raw data as returned by the device."""
        return self.data
