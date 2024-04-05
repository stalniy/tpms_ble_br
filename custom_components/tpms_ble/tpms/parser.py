"""Parser for TPMS BLE advertisements.

"""
from __future__ import annotations
from collections.abc import MutableSequence

import logging
from datetime import datetime
import pytz

from bluetooth_sensor_state_data import BluetoothData
from homeassistant.components.bluetooth import BluetoothServiceInfo
from sensor_state_data import DeviceClass, Units
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
    UnitOfPressure,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = {
    DeviceClass.PRESSURE: SensorEntityDescription(
        key=f"{DeviceClass.PRESSURE}_{Units.PRESSURE_BAR}",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DeviceClass.TEMPERATURE: SensorEntityDescription(
        key=f"{DeviceClass.TEMPERATURE}_{Units.TEMP_CELSIUS}",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DeviceClass.BATTERY: SensorEntityDescription(
        key=f"{DeviceClass.BATTERY}_{Units.PERCENTAGE}",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DeviceClass.SIGNAL_STRENGTH: SensorEntityDescription(
        key=f"{DeviceClass.SIGNAL_STRENGTH}_{Units.SIGNAL_STRENGTH_DECIBELS_MILLIWATT}",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DeviceClass.TIMESTAMP: SensorEntityDescription(
        key="last_updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        name="Last Observed time",
        icon="mdi:clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
}

def _psi_to_bar(value: float):
    return value / 14.5038

def _volt_to_percent(value: float):
    min = 2.0
    if value <= min:
        return 0

    max = 3.0
    result = value * 100 / max
    return result if result <= 100 else 100

def _decode_psi(data: MutableSequence[int]):
    psi_major = data[3] << 8
    psi_minor = data[4] & 255
    psi = psi_major | psi_minor
    return psi - 146 if psi >= 146 else 0

class TpmsBluetoothDeviceData(BluetoothData):
    """Data for TPMS BLE sensors (service 0x27a5)."""

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""

        _LOGGER.debug("Parsing BLE device(%s, %s, %s)", service_info.name, service_info.service_uuids, service_info.address)

        if '000027a5-0000-1000-8000-00805f9b34fb' not in service_info.service_uuids:
            return None

        manufacturer_data = service_info.manufacturer_data
        _LOGGER.debug("Parsing TPMS BLE manufacturer_data data: %s", manufacturer_data)
        address = service_info.address

        self.set_title("TPMS BLE " + service_info.name + " " + address)
        self.set_device_type("TPMS BLE " + str(service_info.name), address)
        self.set_device_name("TPMS " + str(address), address)
        self.set_device_manufacturer("TPMS BLE " + str(service_info.name), address)
        self.set_precision(2)
        self._update_descriptor_value(address, DeviceClass.TIMESTAMP, datetime.now(pytz.utc))

        for key, value in manufacturer_data.items():
            raw = key.to_bytes(2, 'little') + value
            ints = list(raw)

            self._update_descriptor_value(address, DeviceClass.BATTERY, _volt_to_percent(ints[1] / 10.0))
            self._update_descriptor_value(address, DeviceClass.TEMPERATURE, ints[2])
            self._update_descriptor_value(address, DeviceClass.PRESSURE, _psi_to_bar(_decode_psi(ints) / 10.0))

    def _update_descriptor_value(self, address: str, key: DeviceClass, value):
        description = SENSOR_DESCRIPTIONS[key]
        _LOGGER.debug('Upading sensor of %s = %s %s', address, key, value)
        self.update_sensor(
            key,
            description.native_unit_of_measurement,
            value,
            description.device_class,
            device_id=address
        )