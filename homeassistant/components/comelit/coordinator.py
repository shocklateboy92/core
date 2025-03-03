"""Support for Comelit."""

from abc import abstractmethod
from datetime import timedelta
from typing import TypedDict, TypeVar, cast

from aiocomelit import (
    ComeliteSerialBridgeApi,
    ComelitSerialBridgeObject,
    ComelitVedoApi,
    ComelitVedoAreaObject,
    ComelitVedoZoneObject,
    exceptions,
)
from aiocomelit.api import ComelitCommonApi
from aiocomelit.const import ALARM_AREAS, ALARM_ZONES, BRIDGE, VEDO

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import _LOGGER, DOMAIN

type ComelitConfigEntry = ConfigEntry[ComelitBaseCoordinator]


class AlarmDataObject(TypedDict):
    """TypedDict for Alarm data objects."""

    alarm_areas: dict[int, ComelitVedoAreaObject]
    alarm_zones: dict[int, ComelitVedoZoneObject]


T = TypeVar(
    "T",
    bound=dict[str, dict[int, ComelitSerialBridgeObject]] | AlarmDataObject,
)


class ComelitBaseCoordinator(DataUpdateCoordinator[T]):
    """Base coordinator for Comelit Devices."""

    _hw_version: str
    config_entry: ComelitConfigEntry
    api: ComelitCommonApi

    def __init__(
        self, hass: HomeAssistant, entry: ComelitConfigEntry, device: str, host: str
    ) -> None:
        """Initialize the scanner."""

        self._device = device
        self._host = host

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}-{host}-coordinator",
            update_interval=timedelta(seconds=5),
        )
        device_registry = dr.async_get(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            model=device,
            name=f"{device} ({self._host})",
            manufacturer="Comelit",
            hw_version=self._hw_version,
        )

    def platform_device_info(
        self,
        object_class: ComelitVedoZoneObject
        | ComelitVedoAreaObject
        | ComelitSerialBridgeObject,
        object_type: str,
    ) -> dr.DeviceInfo:
        """Set platform device info."""

        return dr.DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self.config_entry.entry_id}-{object_type}-{object_class.index}",
                )
            },
            via_device=(DOMAIN, self.config_entry.entry_id),
            name=object_class.name,
            model=f"{self._device} {object_type}",
            manufacturer="Comelit",
            hw_version=self._hw_version,
        )

    async def _async_update_data(self) -> T:
        """Update device data."""
        _LOGGER.debug("Polling Comelit %s host: %s", self._device, self._host)
        try:
            await self.api.login()
            return await self._async_update_system_data()
        except (exceptions.CannotConnect, exceptions.CannotRetrieveData) as err:
            raise UpdateFailed(repr(err)) from err
        except exceptions.CannotAuthenticate as err:
            raise ConfigEntryAuthFailed from err

    @abstractmethod
    async def _async_update_system_data(self) -> T:
        """Class method for updating data."""


class ComelitSerialBridge(
    ComelitBaseCoordinator[dict[str, dict[int, ComelitSerialBridgeObject]]]
):
    """Queries Comelit Serial Bridge."""

    _hw_version = "20003101"
    api: ComeliteSerialBridgeApi

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ComelitConfigEntry,
        host: str,
        port: int,
        pin: int,
    ) -> None:
        """Initialize the scanner."""
        self.api = ComeliteSerialBridgeApi(host, port, pin)
        super().__init__(hass, entry, BRIDGE, host)

    async def _async_update_system_data(
        self,
    ) -> dict[str, dict[int, ComelitSerialBridgeObject]]:
        """Specific method for updating data."""
        return await self.api.get_all_devices()


class ComelitVedoSystem(ComelitBaseCoordinator[AlarmDataObject]):
    """Queries Comelit VEDO system."""

    _hw_version = "VEDO IP"
    api: ComelitVedoApi

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ComelitConfigEntry,
        host: str,
        port: int,
        pin: int,
    ) -> None:
        """Initialize the scanner."""
        self.api = ComelitVedoApi(host, port, pin)
        super().__init__(hass, entry, VEDO, host)

    async def _async_update_system_data(
        self,
    ) -> AlarmDataObject:
        """Specific method for updating data."""
        data = await self.api.get_all_areas_and_zones()

        return AlarmDataObject(
            alarm_areas=cast(dict[int, ComelitVedoAreaObject], data[ALARM_AREAS]),
            alarm_zones=cast(dict[int, ComelitVedoZoneObject], data[ALARM_ZONES]),
        )
