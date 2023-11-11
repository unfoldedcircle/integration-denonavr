#!/usr/bin/env python3
"""
This module implements a Remote Two integration driver for Denon AVR receivers.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os
from typing import Any

import avr
import config
import setup_flow
import ucapi
from ucapi import MediaPlayer, media_player

_LOG = logging.getLogger("driver")  # avoid having __main__ in log messages
_LOOP = asyncio.get_event_loop()

# Global variables
api = ucapi.IntegrationAPI(_LOOP)
# Map of avr_id -> DenonAVR instance
_configured_avrs: dict[str, avr.DenonAVR] = {}


@api.listens_to(ucapi.Events.CONNECT)
async def on_connect() -> None:
    """When the UCR2 connects, all configured Receiver devices are getting connected."""
    for receiver in _configured_avrs.values():
        # start background task
        _LOOP.create_task(receiver.connect())


@api.listens_to(ucapi.Events.DISCONNECT)
async def on_disconnect():
    """When the UCR2 disconnects, all configured Receiver devices are disconnected."""
    for receiver in _configured_avrs.values():
        # start background task
        _LOOP.create_task(receiver.disconnect())


@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_enter_standby() -> None:
    """
    Enter standby notification.

    Disconnect every Denon AVR instances.
    """
    _LOG.debug("Enter standby event: disconnecting device(s)")
    for configured in _configured_avrs.values():
        await configured.disconnect()


@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_exit_standby() -> None:
    """
    Exit standby notification.

    Connect all Denon AVR instances.
    """
    _LOG.debug("Exit standby event: connecting device(s)")
    # delay is only a temporary workaround, until the core verifies first that the network is up with an IP address
    await asyncio.sleep(2)

    for configured in _configured_avrs.values():
        # start background task
        _LOOP.create_task(configured.connect())


@api.listens_to(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """
    Subscribe to given entities.

    :param entity_ids: entity identifiers.
    """
    _LOG.debug("Subscribe entities event: %s", entity_ids)
    for entity_id in entity_ids:
        avr_id = _avr_from_entity_id(entity_id)
        if avr_id in _configured_avrs:
            receiver = _configured_avrs[avr_id]
            state = media_player_state_from_avr(receiver.state)
            api.configured_entities.update_attributes(entity_id, {media_player.Attributes.STATE: state})
            continue

        device = config.devices.get(avr_id)
        if device:
            _add_configured_avr(device)
        else:
            _LOG.error("Failed to subscribe entity %s: no AVR instance found", avr_id)


# dev device_state_from_avr(avr_state: avr.States) ->
def media_player_state_from_avr(avr_state: avr.States) -> media_player.States:
    """Convert the AVR device state to a media-player entity state."""
    # TODO simplify using a dict
    state = media_player.States.UNKNOWN
    if avr_state == avr.States.ON:
        state = media_player.States.ON
    elif avr_state == avr.States.OFF:
        state = media_player.States.OFF
    elif avr_state == avr.States.PLAYING:
        state = media_player.States.PLAYING
    elif avr_state == avr.States.PAUSED:
        state = media_player.States.PAUSED
    elif avr_state == avr.States.UNAVAILABLE:
        state = media_player.States.UNAVAILABLE
    return state


@api.listens_to(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """On unsubscribe, we disconnect the objects and remove listeners for events."""
    _LOG.debug("Unsubscribe entities event: %s", entity_ids)
    for entity_id in entity_ids:
        avr_id = _avr_from_entity_id(entity_id)
        if avr_id is None:
            continue
        if avr_id in _configured_avrs:
            # TODO #21 this doesn't work once we have more than one entity per device!
            # --- START HACK ---
            # Since an AVR instance only provides exactly one media-player, it's save to disconnect if the entity is
            # unsubscribed. This should be changed to a more generic logic, also as template for other integrations!
            # Otherwise this sets a bad copy-paste example and leads to more issues in the future.
            # --> correct logic: check configured_entities, if empty: disconnect
            _configured_avrs[entity_id].disconnect()
            _configured_avrs[entity_id].events.remove_all_listeners()


async def media_player_cmd_handler(
    entity: MediaPlayer, cmd_id: str, params: dict[str, Any] | None
) -> ucapi.StatusCodes:
    """
    Media-player entity command handler.

    Called by the integration-API if a command is sent to a configured media-player entity.

    :param entity: media-player entity
    :param cmd_id: command
    :param params: optional command parameters
    :return:
    """
    _LOG.info("Got %s command request: %s %s", entity.id, cmd_id, params)

    avr_id = _avr_from_entity_id(entity.id)
    if avr_id is None:
        return ucapi.StatusCodes.NOT_FOUND

    a = _configured_avrs[avr_id]
    if a is None:
        _LOG.warning("No AVR device found for entity: %s", entity.id)
        return ucapi.StatusCodes.SERVICE_UNAVAILABLE

    if cmd_id == media_player.Commands.PLAY_PAUSE:
        res = await a.play_pause()
    elif cmd_id == media_player.Commands.NEXT:
        res = await a.next()
    elif cmd_id == media_player.Commands.PREVIOUS:
        res = await a.previous()
    elif cmd_id == media_player.Commands.VOLUME_UP:
        res = await a.volume_up()
    elif cmd_id == media_player.Commands.VOLUME_DOWN:
        res = await a.volume_down()
    elif cmd_id == media_player.Commands.MUTE_TOGGLE:
        res = await a.mute(not entity.attributes[media_player.Attributes.MUTED])
    elif cmd_id == media_player.Commands.ON:
        res = await a.power_on()
    elif cmd_id == media_player.Commands.OFF:
        res = await a.power_off()
    elif cmd_id == media_player.Commands.SELECT_SOURCE:
        res = await a.set_input(params["source"])
    else:
        return ucapi.StatusCodes.NOT_IMPLEMENTED

    return res


def _key_update_helper(key: str, value: str | None, attributes, configured_entity):
    if value is None:
        return attributes

    if key in configured_entity.attributes:
        if configured_entity.attributes[key] != value:
            attributes[key] = value
    else:
        attributes[key] = value

    return attributes


async def on_avr_connected(avr_id: str):
    """Handle AVR connection."""
    _LOG.debug("AVR connected: %s", avr_id)

    if avr_id not in _configured_avrs:
        _LOG.warning("Configured AVR %s is not configured", avr_id)
        return

    # TODO #21 when multiple devices are supported, the device state logic isn't that simple anymore!
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)

    for entity_id in _entities_from_avr(avr_id):
        configured_entity = api.configured_entities.get(entity_id)
        if configured_entity is None:
            continue

        if configured_entity.entity_type == ucapi.EntityTypes.MEDIA_PLAYER:
            if configured_entity.attributes[media_player.Attributes.STATE] == media_player.States.UNAVAILABLE:
                # TODO why STANDBY?
                api.configured_entities.update_attributes(
                    entity_id, {media_player.Attributes.STATE: media_player.States.STANDBY}
                )


async def on_avr_disconnected(avr_id: str):
    """Handle AVR disconnection."""
    _LOG.debug("AVR disconnected: %s", avr_id)

    for entity_id in _entities_from_avr(avr_id):
        configured_entity = api.configured_entities.get(entity_id)
        if configured_entity is None:
            continue

        if configured_entity.entity_type == ucapi.EntityTypes.MEDIA_PLAYER:
            # TODO why STANDBY?
            api.configured_entities.update_attributes(
                entity_id, {media_player.Attributes.STATE: media_player.States.STANDBY}
            )

    # TODO #21 when multiple devices are supported, the device state logic isn't that simple anymore!
    await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)


async def on_avr_connection_error(avr_id: str, message):
    """Set entities of AVR to state UNAVAILABLE if AVR connection error occurred."""
    _LOG.error(message)

    for entity_id in _entities_from_avr(avr_id):
        configured_entity = api.configured_entities.get(entity_id)
        if configured_entity is None:
            continue

        if configured_entity.entity_type == ucapi.EntityTypes.MEDIA_PLAYER:
            api.configured_entities.update_attributes(
                entity_id, {media_player.Attributes.STATE: media_player.States.UNAVAILABLE}
            )

    # TODO #21 when multiple devices are supported, the device state logic isn't that simple anymore!
    await api.set_device_state(ucapi.DeviceStates.ERROR)


async def on_avr_update(avr_id: str, update: dict[str, Any]) -> None:
    """
    Update attributes of configured media-player entity if AVR properties changed.

    :param avr_id: AVR identifier
    :param update: dictionary containing the updated properties
    """
    _LOG.debug("[%s] AVR update: %s", avr_id, update)

    attributes = None

    for entity_id in _entities_from_avr(avr_id):
        # TODO why not also update available entities?
        configured_entity = api.configured_entities.get(entity_id)
        if configured_entity is None:
            return

        if configured_entity.entity_type == ucapi.EntityTypes.MEDIA_PLAYER:
            attributes = _update_media_player(configured_entity, update)

        if attributes:
            api.configured_entities.update_attributes(entity_id, attributes)


def _update_media_player(configured_entity: ucapi.Entity, update) -> dict[str, any]:
    attributes = {}

    if "state" in update:
        state = _get_media_player_state(update["state"])
        attributes = _key_update_helper(media_player.Attributes.STATE, state, attributes, configured_entity)

    if "artist" in update:
        attributes = _key_update_helper(
            media_player.Attributes.MEDIA_ARTIST, update["artist"], attributes, configured_entity
        )
    if "album" in update:
        attributes = _key_update_helper(
            media_player.Attributes.MEDIA_ALBUM, update["album"], attributes, configured_entity
        )
    if "artwork" in update:
        attributes[media_player.Attributes.MEDIA_IMAGE_URL] = update["artwork"]
    if "title" in update:
        attributes = _key_update_helper(
            media_player.Attributes.MEDIA_TITLE, update["title"], attributes, configured_entity
        )
    # if "position" in update:
    #     attributes = keyUpdateHelper(media_player.Attributes.MEDIA_POSITION, update["position"], attributes,
    #                                  configuredEntity)
    # if "total_time" in update:
    #     attributes = keyUpdateHelper(media_player.Attributes.MEDIA_DURATION, update["total_time"],
    #                                  attributes, configuredEntity)
    if "muted" in update:
        attributes[media_player.Attributes.MUTED] = update["muted"]
    if "source" in update:
        attributes = _key_update_helper(media_player.Attributes.SOURCE, update["source"], attributes, configured_entity)
    if "source_list" in update:
        if media_player.Attributes.SOURCE_LIST in configured_entity.attributes:
            # TODO optimize: only set if changed
            attributes[media_player.Attributes.SOURCE_LIST] = update["source_list"]

    if media_player.Features.SELECT_SOUND_MODE in configured_entity.features:
        if "sound_mode" in update:
            attributes = _key_update_helper(
                media_player.Attributes.SOUND_MODE, update["sound_mode"], attributes, configured_entity
            )
        if "sound_mode_list" in update:
            if media_player.Attributes.SOUND_MODE_LIST in configured_entity.attributes:
                # TODO optimize: only set if changed
                attributes[media_player.Attributes.SOUND_MODE_LIST] = update["sound_mode_list"]
    if "volume" in update:
        attributes = _key_update_helper(media_player.Attributes.VOLUME, update["volume"], attributes, configured_entity)

    _update_attributes(attributes, ucapi.EntityTypes.MEDIA_PLAYER)

    return attributes


def _avr_from_entity_id(entity_id: str) -> str | None:
    """
    Return the avr_id prefix of an entity_id.

    The prefix is the part before the first dot in the name and refers to the AVR device identifier.

    :param entity_id: the entity identifier
    :return: the device prefix, or None if entity_id doesn't contain a dot
    """
    return entity_id.split(".", 1)[1]


def _entities_from_avr(avr_id: str) -> list[str]:
    """
    Return all associated entity identifiers of the given AVR.

    :param avr_id: the AVR identifier
    :return: list of entity identifiers
    """
    # dead simple for now: one media_player entity per device!
    return [f"media_player.{avr_id}"]


def _get_media_player_state(avr_state) -> media_player.States:
    """
    Convert AVR state to UC API media-player state.

    :param avr_state: Denon AVR state
    :return: UC API media_player state
    """
    state = media_player.States.UNKNOWN

    if avr_state == avr.States.ON:
        state = media_player.States.ON
    elif avr_state == avr.States.PLAYING:
        state = media_player.States.PLAYING
    elif avr_state == avr.States.PAUSED:
        state = media_player.States.PAUSED
    elif avr_state == avr.States.OFF:
        state = media_player.States.OFF

    return state


def _update_attributes(attributes, entity_type: ucapi.EntityTypes):
    """
    Update the entity attributes based on entity type and the state attribute.

    :param attributes: entity attributes dictionary
    :param entity_type: the entity type
    """
    if entity_type == ucapi.EntityTypes.MEDIA_PLAYER and media_player.Attributes.STATE in attributes:
        if attributes[media_player.Attributes.STATE] == media_player.States.OFF:
            attributes[media_player.Attributes.MEDIA_IMAGE_URL] = ""
            attributes[media_player.Attributes.MEDIA_ALBUM] = ""
            attributes[media_player.Attributes.MEDIA_ARTIST] = ""
            attributes[media_player.Attributes.MEDIA_TITLE] = ""
            attributes[media_player.Attributes.MEDIA_TYPE] = ""
            attributes[media_player.Attributes.SOURCE] = ""
            # attributes[media_player.Attributes.MEDIA_DURATION] = 0


def _create_entity_id(avr_id: str, entity_type: ucapi.EntityTypes) -> str:
    return f"{entity_type.value}.{avr_id}"


def _add_configured_avr(device: config.AvrDevice, connect: bool = True) -> None:
    # the device should not yet be configured, but better be safe
    if device.id in _configured_avrs:
        receiver = _configured_avrs[device.id]
        receiver.disconnect()
    else:
        receiver = avr.DenonAVR(device, loop=_LOOP)

        receiver.events.on(avr.Events.CONNECTED, on_avr_connected)
        receiver.events.on(avr.Events.DISCONNECTED, on_avr_disconnected)
        receiver.events.on(avr.Events.ERROR, on_avr_connection_error)
        receiver.events.on(avr.Events.UPDATE, on_avr_update)

        _configured_avrs[device.id] = receiver

    async def start_connection():
        # res = await receiver.init()
        # if res is False:
        #     await api.set_device_state(ucapi.DeviceStates.ERROR)
        await receiver.connect()

    if connect:
        # start background task
        _LOOP.create_task(start_connection())

    _register_available_entities(device)


def _register_available_entities(device: config.AvrDevice) -> None:
    """
    Create entities for given receiver device and register them as available entities.

    :param avr_id: Receiver identifier
    :param name: Receiver device name
    """
    # plain and simple for now: only one media_player per AVR device
    entity_id = _create_entity_id(device.id, ucapi.EntityTypes.MEDIA_PLAYER)
    features = [
        media_player.Features.ON_OFF,
        media_player.Features.VOLUME,
        media_player.Features.VOLUME_UP_DOWN,
        media_player.Features.MUTE_TOGGLE,
        media_player.Features.PLAY_PAUSE,
        media_player.Features.NEXT,
        media_player.Features.PREVIOUS,
        # media_player.Features.MEDIA_DURATION,
        # media_player.Features.MEDIA_POSITION,
        media_player.Features.MEDIA_TITLE,
        media_player.Features.MEDIA_ARTIST,
        media_player.Features.MEDIA_ALBUM,
        media_player.Features.MEDIA_IMAGE_URL,
        media_player.Features.MEDIA_TYPE,
        media_player.Features.SELECT_SOURCE,
    ]
    attributes = {
        media_player.Attributes.STATE: media_player.States.UNAVAILABLE,
        media_player.Attributes.VOLUME: 0,
        media_player.Attributes.MUTED: False,
        # media_player.Attributes.MEDIA_DURATION: 0,
        # media_player.Attributes.MEDIA_POSITION: 0,
        media_player.Attributes.MEDIA_IMAGE_URL: "",
        media_player.Attributes.MEDIA_TITLE: "",
        media_player.Attributes.MEDIA_ARTIST: "",
        media_player.Attributes.MEDIA_ALBUM: "",
        media_player.Attributes.SOURCE: "",
        media_player.Attributes.SOURCE_LIST: [],
    }
    if device.support_sound_mode:
        features.append(media_player.Features.SELECT_SOUND_MODE)
        attributes[media_player.Attributes.SOUND_MODE] = ""
        attributes[media_player.Attributes.SOUND_MODE_LIST] = []

    entity = MediaPlayer(
        entity_id,
        device.name,
        features,
        attributes,
        device_class=media_player.DeviceClasses.RECEIVER,
        cmd_handler=media_player_cmd_handler,
    )

    if api.available_entities.contains(entity.id):
        api.available_entities.remove(entity.id)
    api.available_entities.add(entity)


def on_device_added(device: config.AvrDevice) -> None:
    """Handle a newly added device in the configuration."""
    _LOG.debug("New device added: %s", device)
    _add_configured_avr(device, connect=False)


async def async_disconnect(receiver: avr.DenonAVR) -> None:
    """Disconnect from receiver and remove all listeners."""
    await receiver.disconnect()
    receiver.events.remove_all_listeners()


def on_device_removed(device: config.AvrDevice | None) -> None:
    """Handle a removed device in the configuration."""
    if device is None:
        _LOG.debug("Configuration cleared, disconnecting & removing all configured AVR instances")
        for configured in _configured_avrs.values():
            _LOOP.create_task(async_disconnect(configured))
        _configured_avrs.clear()
        api.configured_entities.clear()
        api.available_entities.clear()
    else:
        if device.id in _configured_avrs:
            _LOG.debug("Disconnecting from removed AVR %s", device.id)
            configured = _configured_avrs.pop(device.id)
            _LOOP.create_task(async_disconnect(configured))
            for entity_id in _entities_from_avr(configured.id):
                api.configured_entities.remove(entity_id)
                api.available_entities.remove(entity_id)


async def main():
    """Start the Remote Two integration driver."""
    logging.basicConfig()

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("denonavr.ssdp").setLevel(level)
    logging.getLogger("avr").setLevel(level)
    logging.getLogger("discover").setLevel(level)
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("setup_flow").setLevel(level)

    config.devices = config.Devices(api.config_dir_path, on_device_added, on_device_removed)
    for device in config.devices.all():
        _add_configured_avr(device, connect=False)

    await api.init("driver.json", setup_flow.driver_setup_handler)


if __name__ == "__main__":
    _LOOP.run_until_complete(main())
    _LOOP.run_forever()
