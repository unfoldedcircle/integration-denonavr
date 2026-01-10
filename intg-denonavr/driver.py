#!/usr/bin/env python3
"""
This module implements a Remote Two/3 integration driver for Denon/Marantz AVR receivers.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os
from typing import Any

import avr
import config
import denon_remote
import media_player
import sensor
import setup_flow
import ucapi
from config import AdditionalEventType, SensorType, avr_from_entity_id, create_entity_id
from entities import DenonEntity
from i18n import _a
from ucapi.media_player import Attributes as MediaAttr

_LOG = logging.getLogger("driver")  # avoid having __main__ in log messages
_LOOP = asyncio.get_event_loop()

# Global variables
api = ucapi.IntegrationAPI(_LOOP)
# Map of avr_id -> DenonAVR instance
_configured_avrs: dict[str, avr.DenonDevice] = {}
# pylint: disable=C0103
_REMOTE_IN_STANDBY = False


async def receiver_status_poller(interval: float = 10.0) -> None:
    """Receiver data poller."""
    # TODO: is it important to delay the first call?
    while True:
        start_time = asyncio.get_event_loop().time()
        if not _REMOTE_IN_STANDBY:
            try:
                tasks = [
                    receiver.async_update_receiver_data()
                    for receiver in _configured_avrs.values()
                    # pylint: disable=W0212
                    if receiver.active and not (receiver._telnet_healthy)
                ]
                await asyncio.gather(*tasks)
            except (KeyError, ValueError):  # TODO check parallel access / modification while iterating a dict
                pass
        elapsed_time = asyncio.get_event_loop().time() - start_time
        await asyncio.sleep(min(10.0, max(1.0, interval - elapsed_time)))


@api.listens_to(ucapi.Events.CONNECT)
async def on_r2_connect_cmd() -> None:
    """Connect all configured receivers when the Remote Two/3 sends the connect command."""
    _LOG.debug("R2 connect command: connecting device(s)")
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)  # just to make sure the device state is set
    for receiver in _configured_avrs.values():
        # start background task
        _LOOP.create_task(receiver.connect())


@api.listens_to(ucapi.Events.DISCONNECT)
async def on_r2_disconnect_cmd():
    """Disconnect all configured receivers when the Remote Two/3 sends the disconnect command."""
    for receiver in _configured_avrs.values():
        # start background task
        _LOOP.create_task(receiver.disconnect())


@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_r2_enter_standby() -> None:
    """
    Enter standby notification from Remote Two/3.

    Disconnect every Denon/Marantz AVR instances.
    """
    global _REMOTE_IN_STANDBY

    _REMOTE_IN_STANDBY = True
    _LOG.debug("Enter standby event: disconnecting device(s)")
    for configured in _configured_avrs.values():
        await configured.disconnect()


@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_r2_exit_standby() -> None:
    """
    Exit standby notification from Remote Two/3.

    Connect all Denon/Marantz AVR instances.
    """
    global _REMOTE_IN_STANDBY

    _REMOTE_IN_STANDBY = False
    _LOG.debug("Exit standby event: connecting device(s)")

    for configured in _configured_avrs.values():
        # start background task
        _LOOP.create_task(configured.connect())


@api.listens_to(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """
    Subscribe to given entities.

    :param entity_ids: entity identifiers.
    """
    global _REMOTE_IN_STANDBY

    _REMOTE_IN_STANDBY = False
    _LOG.debug("Subscribe entities event: %s", entity_ids)
    # force an entity change event with the current state for all subscribed entities
    for entity_id in entity_ids:
        avr_id = avr_from_entity_id(entity_id)
        if avr_id in _configured_avrs:
            receiver = _configured_avrs[avr_id]
            configured_entity = api.configured_entities.get(entity_id)
            if configured_entity is None:
                continue
            if isinstance(configured_entity, DenonEntity):
                state = configured_entity.state_from_avr(receiver.state)
                # It doesn't matter if we use the media_player.Attributes enum. It's called the same for all entities
                configured_entity.update_attributes({ucapi.media_player.Attributes.STATE: state}, force=True)
            continue

        device = config.devices.get(avr_id)
        if device:
            _configure_new_avr(device, connect=True)
        else:
            _LOG.error("Failed to subscribe entity %s: no AVR configuration found", entity_id)


@api.listens_to(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """On unsubscribe, we disconnect the devices and remove listeners for events."""
    _LOG.debug("Unsubscribe entities event: %s", entity_ids)
    avrs_to_remove = set()
    for entity_id in entity_ids:
        avr_id = avr_from_entity_id(entity_id)
        if avr_id is None:
            continue
        avrs_to_remove.add(avr_id)

    # Keep devices that are used by other configured entities not in this list
    for entity in api.configured_entities.get_all():
        entity_id = entity.get("entity_id", "")
        if entity_id in entity_ids:
            continue
        avr_id = avr_from_entity_id(entity_id)
        if avr_id is None:
            continue
        if avr_id in avrs_to_remove:
            avrs_to_remove.remove(avr_id)

    for avr_id in avrs_to_remove:
        if avr_id in _configured_avrs:
            await _configured_avrs[avr_id].disconnect()
            _configured_avrs[avr_id].events.remove_all_listeners()


async def on_avr_connected(avr_id: str):
    """Handle AVR connection."""
    _LOG.debug("AVR connected: %s", avr_id)

    if avr_id not in _configured_avrs:
        _LOG.warning("AVR %s is not configured", avr_id)
        return

    await api.set_device_state(ucapi.DeviceStates.CONNECTED)  # just to make sure the device state is set

    # set the initial entity state to UNKNOWN, concrete state is set when updates are triggered / fetched
    update = {MediaAttr.STATE: avr.States.UNKNOWN}
    for entity in _configured_entities_from_device(avr_id):
        if isinstance(entity, DenonEntity):
            entity.update_attributes(update)


def on_avr_disconnected(avr_id: str):
    """Handle AVR disconnection."""
    _LOG.debug("AVR disconnected: %s", avr_id)
    _mark_entities_unavailable(avr_id, force=True)


def on_avr_connection_error(avr_id: str, message):
    """Set entities of AVR to state UNAVAILABLE if AVR connection error occurred."""
    _LOG.error(message)
    _mark_entities_unavailable(avr_id, force=False)


def _mark_entities_unavailable(avr_id: str, *, force: bool):
    for entity in _configured_entities_from_device(avr_id):
        if isinstance(entity, DenonEntity):
            entity.update_attributes(
                {ucapi.media_player.Attributes.STATE: ucapi.media_player.States.UNAVAILABLE}, force=force
            )


def handle_avr_address_change(avr_id: str, address: str) -> None:
    """Update device configuration with changed IP address."""
    device = config.devices.get(avr_id)
    if device and device.address != address:
        _LOG.info("Updating IP address of configured AVR %s: %s -> %s", avr_id, device.address, address)
        device.address = address
        config.devices.update(device)


def on_avr_update(avr_id: str, update: dict[str, Any] | None) -> None:
    """
    Update attributes of configured media-player entity if AVR properties changed.

    :param avr_id: AVR identifier
    :param update: dictionary containing the updated properties or None if
    """
    if update is None:
        if avr_id not in _configured_avrs:
            return
        receiver = _configured_avrs[avr_id]
        update = {
            MediaAttr.STATE: receiver.state,
            MediaAttr.MEDIA_ARTIST: receiver.media_artist,
            MediaAttr.MEDIA_ALBUM: receiver.media_album_name,
            MediaAttr.MEDIA_IMAGE_URL: receiver.media_image_url,
            MediaAttr.MEDIA_TITLE: receiver.media_title,
            MediaAttr.MUTED: receiver.is_volume_muted,
            MediaAttr.SOURCE: receiver.source,
            MediaAttr.SOURCE_LIST: receiver.source_list,
            MediaAttr.SOUND_MODE: receiver.sound_mode,
            AdditionalEventType.RAW_SOUND_MODE: receiver.sound_mode_raw,
            MediaAttr.SOUND_MODE_LIST: receiver.sound_mode_list,
            MediaAttr.VOLUME: receiver.volume_level,
            AdditionalEventType.SLEEP_TIMER: receiver.sleep,
            AdditionalEventType.AUDIO_DELAY: receiver.audio_delay,
            AdditionalEventType.MONITOR: receiver.video_output,
            AdditionalEventType.DIMMER: receiver.dimmer,
            AdditionalEventType.ECO_MODE: receiver.eco_mode,
            AdditionalEventType.VIDEO_SIGNAL_IN: receiver.video_hdmi_signal_in,
            AdditionalEventType.VIDEO_SIGNAL_OUT: receiver.video_hdmi_signal_out,
            AdditionalEventType.AUDIO_SAMPLING_RATE: receiver.audio_sampling_rate,
            AdditionalEventType.AUDIO_SIGNAL: receiver.audio_signal,
            AdditionalEventType.AUDIO_SOUND: receiver.audio_sound,
            AdditionalEventType.INPUT_CHANNELS: receiver.input_channels,
            AdditionalEventType.OUTPUT_CHANNELS: receiver.output_channels,
            AdditionalEventType.MAX_RESOLUTION: receiver.max_resolution,
        }
    else:
        _LOG.info("[%s] AVR update: %s", avr_id, update)

    for entity in _configured_entities_from_device(avr_id):
        if isinstance(entity, DenonEntity):
            entity.update_attributes(update)


MAPPED_AVR_ENTITIES = {}


def _entities_from_avr(avr_id: str) -> list[str]:
    """
    Return all associated entity identifiers of the given AVR.

    :param avr_id: the AVR identifier
    :return: list of entity identifiers
    """
    # dead simple for now: one media_player entity per device!
    # TODO #21 support multiple zones: one media-player per zone
    avr_entities = MAPPED_AVR_ENTITIES.get(avr_id)
    if avr_entities is None:
        avr_entities = [
            create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER),
            create_entity_id(avr_id, ucapi.EntityTypes.REMOTE),
            *(create_entity_id(avr_id, ucapi.EntityTypes.SENSOR, sensor_type.value) for sensor_type in SensorType),
        ]
        MAPPED_AVR_ENTITIES[avr_id] = avr_entities
    return avr_entities


def _configure_new_avr(device: config.AvrDevice, connect: bool = True) -> None:
    """
    Create and configure a new AVR device.

    Supported entities of the device are created and registered in the integration library as available entities.

    :param device: the receiver configuration.
    :param connect: True: start connection to receiver.
    """
    # the device should not yet be configured, but better be safe
    if device.id in _configured_avrs:
        receiver = _configured_avrs[device.id]
        if not connect:
            _LOOP.create_task(receiver.disconnect())
    else:
        receiver = avr.DenonDevice(device, loop=_LOOP)

        receiver.events.on(avr.Events.CONNECTED, on_avr_connected)
        receiver.events.on(avr.Events.DISCONNECTED, on_avr_disconnected)
        receiver.events.on(avr.Events.ERROR, on_avr_connection_error)
        receiver.events.on(avr.Events.UPDATE, on_avr_update)
        receiver.events.on(avr.Events.IP_ADDRESS_CHANGED, handle_avr_address_change)

        _configured_avrs[device.id] = receiver

    if connect:
        # start background connection task
        _LOOP.create_task(receiver.connect())

    _register_available_entities(device, receiver)


def _register_available_entities(device: config.AvrDevice, receiver: avr.DenonDevice) -> None:
    """
    Create entities for given receiver device and register them as available entities.

    :param device: Receiver
    """
    # plain and simple for now: only one media_player per AVR device
    denon_media_player = media_player.DenonMediaPlayer(device, receiver, api)
    entities: list[media_player.DenonMediaPlayer | denon_remote.DenonRemote | sensor.DenonSensor] = [
        denon_media_player,
        denon_remote.DenonRemote(device, receiver, denon_media_player, api),
        *sensor.create_sensors(device, receiver, api),
    ]

    for entity in entities:
        if api.available_entities.contains(entity.id):
            api.available_entities.remove(entity.id)
        api.available_entities.add(entity)


def on_device_added(device: config.AvrDevice) -> None:
    """Handle a newly added device in the configuration."""
    _LOG.debug("New device added: %s", device)
    _LOOP.create_task(api.set_device_state(ucapi.DeviceStates.CONNECTED))  # just to make sure the device state is set
    _configure_new_avr(device, connect=False)


def on_device_removed(device: config.AvrDevice | None) -> None:
    """Handle a removed device in the configuration."""
    if device is None:
        _LOG.debug("Configuration cleared, disconnecting & removing all configured AVR instances")
        for configured in _configured_avrs.values():
            _LOOP.create_task(_async_remove(configured))
        _configured_avrs.clear()
        api.configured_entities.clear()
        api.available_entities.clear()
    else:
        if device.id in _configured_avrs:
            _LOG.debug("Disconnecting from removed AVR %s", device.id)
            configured = _configured_avrs.pop(device.id)
            _LOOP.create_task(_async_remove(configured))
            for entity_id in _entities_from_avr(configured.id):
                api.configured_entities.remove(entity_id)
                api.available_entities.remove(entity_id)


async def _async_remove(receiver: avr.DenonDevice) -> None:
    """Disconnect from receiver and remove all listeners."""
    await receiver.disconnect()
    receiver.events.remove_all_listeners()


def _configured_entities_from_device(avr_id: str) -> list[ucapi.Entity]:
    """
    Return all configured entities of the given device.

    :param avr_id: the avr identifier
    :return: list of configured entities
    """
    entities = []
    for entity_id in _entities_from_avr(avr_id):
        configured_entity = api.configured_entities.get(entity_id)
        if configured_entity:
            entities.append(configured_entity)
    return entities


class JournaldFormatter(logging.Formatter):
    """Formatter for journald. Prefixes messages with priority level."""

    def format(self, record):
        """Format the log record with journald priority prefix."""
        # mapping of logging levels to journald priority levels
        # https://www.freedesktop.org/software/systemd/man/latest/sd-daemon.html#syslog-compatible-log-levels
        priority = {
            logging.DEBUG: "<7>",
            logging.INFO: "<6>",
            logging.WARNING: "<4>",
            logging.ERROR: "<3>",
            logging.CRITICAL: "<2>",
        }.get(record.levelno, "<6>")
        return f"{priority}{record.name}: {record.getMessage()}"


async def main():
    """Start the Remote Two/3 integration driver."""
    if os.getenv("INVOCATION_ID"):
        # when running under systemd: timestamps are added by the journal
        # and we use a custom formatter for journald priority levels
        handler = logging.StreamHandler()
        handler.setFormatter(JournaldFormatter())
        logging.basicConfig(handlers=[handler])
    else:
        logging.basicConfig(
            format="%(asctime)s.%(msecs)03d %(levelname)-5s %(name)s.%(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("denonavr.ssdp").setLevel(level)
    logging.getLogger("denonavr").setLevel("INFO")
    logging.getLogger("avr").setLevel(level)
    logging.getLogger("denon_remote").setLevel(level)
    logging.getLogger("discover").setLevel(level)
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("media_player").setLevel(level)
    logging.getLogger("receiver").setLevel(level)
    logging.getLogger("setup_flow").setLevel(level)
    logging.getLogger("sensor").setLevel(level)

    config.devices = config.Devices(api.config_dir_path, on_device_added, on_device_removed)
    for device in config.devices.all():
        _configure_new_avr(device, connect=False)

    # Note: this is useful when using telnet in case the connection is unhealthy
    # and changes are made from another source
    _LOOP.create_task(receiver_status_poller())

    await api.init("driver.json", setup_flow.driver_setup_handler)

    # temporary hack to change driver.json language texts until supported by the wrapper lib # pylint: disable=W0212
    api._driver_info["description"] = _a("Control your Denon or Marantz AVRs with Remote Two/3.")
    api._driver_info["setup_data_schema"] = setup_flow.setup_data_schema()  # pylint: disable=W0212


if __name__ == "__main__":
    _LOOP.run_until_complete(main())
    _LOOP.run_forever()
