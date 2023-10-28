#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module implements a Remote Two integration driver for Denon AVR receivers.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import json
import logging
import os

import avr
import ucapi
from ucapi import media_player

_LOG = logging.getLogger("driver")  # avoid having __main__ in log messages
_LOOP = asyncio.get_event_loop()

_CFG_FILENAME = "config.json"
# Global variables
_CFG_FILE_PATH: str | None = None
api = ucapi.IntegrationAPI(_LOOP)
_config: list[dict[str, any]] = []
# Map of avr_id -> DenonAVR instance
_configured_avrs: dict[str, avr.DenonAVR] = {}


async def clear_config():
    """Remove the configuration file."""
    global _config
    _config = []

    if os.path.exists(_CFG_FILE_PATH):
        os.remove(_CFG_FILE_PATH)


async def store_config() -> bool:
    """
    Store the configuration file.

    :return: True if the configuration could be saved.
    """
    try:
        with open(_CFG_FILE_PATH, "w+", encoding="utf-8") as f:
            json.dump(_config, f, ensure_ascii=False)
        return True
    except OSError:
        _LOG.error("Cannot write the config file")

    return False


async def load_config():
    """
    Load the config into the config global variable.

    :return: True if the configuration could be loaded.
    """
    global _config

    try:
        with open(_CFG_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _config = data
        return True
    except OSError:
        _LOG.error("Cannot open the config file")
    except ValueError:
        _LOG.error("Empty or invalid config file")

    return False


# DRIVER SETUP
# TODO redesign API for better dev UX
# - Return object must be the next step in the setup flow.
# - The client should not have to know or call driver_setup_error / request_driver_setup_user_input!
# - Don't expose websocket.
@api.events.on(ucapi.Events.SETUP_DRIVER)
async def _on_setup_driver(websocket, req_id: int, _data) -> None:
    """
    Remote Two request callback to setup the driver.

    :param websocket: client connection
    :param req_id: request id
    :param _data: not used
    """
    _LOG.debug("Starting driver setup")
    await clear_config()
    await api.acknowledge_command(websocket, req_id)
    await api.driver_setup_progress(websocket)

    _LOG.debug("Starting discovery")
    avrs = await avr.discover_denon_avrs()
    dropdown_items = []

    for a in avrs:
        avr_data = {"id": a["host"], "label": {"en": f"{a['friendlyName']} ({a['modelName']}) [{a['host']}]"}}
        dropdown_items.append(avr_data)

    if not dropdown_items:
        _LOG.warning("No AVRs found")
        # TODO can't we use a NOT_FOUND error to clearly indicate that nothing was found?
        #      Otherwise, this looks like an internal error to the user.
        await api.driver_setup_error(websocket)
        return

    await api.request_driver_setup_user_input(
        websocket,
        {"en": "Please choose your Denon AVR", "de": "Bitte Denon AVR auswählen"},
        [
            {
                "field": {"dropdown": {"value": dropdown_items[0]["id"], "items": dropdown_items}},
                "id": "choice",
                "label": {
                    "en": "Choose your Denon AVR",
                    "de": "Wähle deinen Denon AVR",
                    "fr": "Choisissez votre Denon AVR",
                },
            }
        ],
    )


# TODO redesign API for better dev UX
# - Return object must be the next step in the setup flow.
# - The client should not have to know or call driver_setup_complete / driver_setup_error!
# - Don't expose websocket.
@api.events.on(ucapi.Events.SETUP_DRIVER_USER_DATA)
async def _on_setup_driver_user_data(websocket, req_id: int, data):
    await api.acknowledge_command(websocket, req_id)
    await api.driver_setup_progress(websocket)

    if "choice" in data:
        choice = data["choice"]
        _LOG.debug("Chosen Denon AVR: %s", choice)

        obj = avr.DenonAVR(_LOOP, choice)
        # FIXME handle connect error!
        await obj.connect()
        _configured_avrs[obj.id] = obj

        _add_available_entity(obj.id, obj.name)

        _config.append({"id": obj.id, "name": obj.name, "ipaddress": obj.ipaddress})
        await store_config()

        await api.driver_setup_complete(websocket)
    else:
        _LOG.error("No choice was received")
        await api.driver_setup_error(websocket)


# When the core connects, we just set the device state
@api.events.on(ucapi.Events.CONNECT)
async def _on_connect():
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)


# When the core disconnects, we just set the device state
@api.events.on(ucapi.Events.DISCONNECT)
async def _on_disconnect():
    # TODO why disconnect all AVR connections if the integration WS connection to UCR2 disconnects?
    #      This can cause issues and longer reconnect attempts. At least keep the AVR connections up for a certain time!
    _LOG.debug("Client disconnected, disconnecting all AVRs")
    for configured in _configured_avrs.values():
        configured.events.remove_all_listeners()
        await configured.disconnect()

    await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)


# On standby, we disconnect every Denon AVR objects
@api.events.on(ucapi.Events.ENTER_STANDBY)
async def _on_enter_standby():
    for configured in _configured_avrs.values():
        await configured.disconnect()


# On exit standby we wait a bit then connect all Denon AVR objects
@api.events.on(ucapi.Events.EXIT_STANDBY)
async def _on_exit_standby():
    await asyncio.sleep(2)

    for configured in _configured_avrs.values():
        await configured.connect()


# When the core subscribes to entities, we set these to UNAVAILABLE state
# then we hook up to the signals of the object and then connect
@api.events.on(ucapi.Events.SUBSCRIBE_ENTITIES)
async def _on_subscribe_entities(entity_ids: list[str]):
    # TODO verify if this is correct: pylint complains about `entity_id` and `a` being cell-var-from-loop
    # https://pylint.readthedocs.io/en/latest/user_guide/messages/warning/cell-var-from-loop.html
    for entity_id in entity_ids:
        if not entity_id.startswith("media_player."):
            _LOG.warning("Cannot subscribe to unknown entity: %s", entity_id)
            continue

        configured_id = _avr_from_entity_id(entity_id)

        if configured_id not in _configured_avrs:
            _LOG.warning("Cannot subscribe entity '%s' to AVR events: AVR not configured", entity_id)
            continue

        _LOG.debug("Subscribing entity '%s' to AVR events", entity_id)
        a = _configured_avrs[configured_id]

        @a.events.on(avr.Events.CONNECTED)
        async def on_connected(avr_id: str):
            await _handle_connected(avr_id)

        @a.events.on(avr.Events.DISCONNECTED)
        async def on_disconnected(avr_id: str):
            await _handle_disconnected(avr_id)

        @a.events.on(avr.Events.ERROR)
        async def on_error(avr_id: str, message):
            await _handle_connection_error(avr_id, message)

        @a.events.on(avr.Events.UPDATE)
        async def on_update(update):
            # FIXME W0640: Cell variable entity_id defined in loop (cell-var-from-loop)
            #       This is most likely the WRONG entity_id if we have MULTIPLE configuredAVRs
            await _handle_avr_update(configured_id, update)

        await a.connect()

        api.configured_entities.update_attributes(
            entity_id,
            {
                media_player.Attributes.STATE: _media_player_state_from_avr(a.state),
                media_player.Attributes.SOURCE_LIST: a.input_list,
                media_player.Attributes.SOURCE: a.input,
                media_player.Attributes.VOLUME: a.volume,
                media_player.Attributes.MEDIA_ARTIST: a.artist,
                media_player.Attributes.MEDIA_TITLE: a.title,
                media_player.Attributes.MEDIA_IMAGE_URL: a.artwork,
            },
        )


def _media_player_state_from_avr(avr_state: avr.States) -> media_player.States:
    """Convert the AVR device state to a media-player entity state."""
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


# On unsubscribe, we disconnect the objects and remove listeners for events
@api.events.on(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def _on_unsubscribe_entities(entity_ids):
    for entity_id in entity_ids:
        avr_id = _avr_from_entity_id(entity_id)
        if avr_id is None:
            continue
        if avr_id in _configured_avrs:
            _LOG.debug("Unsubscribing entity `%s` from events", entity_id)
            a = _configured_avrs[avr_id]
            # TODO this doesn't work once we have more than one entity per device!
            a.events.remove_all_listeners()
            await a.disconnect()


# We handle commands here
@api.events.on(ucapi.Events.ENTITY_COMMAND)
async def _on_entity_command(websocket, req_id: int, entity_id: str, _entity_type, cmd_id: str, params):
    configured_entity = api.configured_entities.get(entity_id)
    if configured_entity is None:
        _LOG.warning("Cannot execute command '%s' for '%s': no configured entity found", cmd_id, entity_id)
        return

    avr_id = _avr_from_entity_id(entity_id)
    if avr_id is None:
        return

    a = _configured_avrs[avr_id]
    if a is None:
        _LOG.warning("No AVR device found for entity: %s", entity_id)
        return

    if cmd_id == media_player.Commands.PLAY_PAUSE:
        res = await a.play_pause()
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.NEXT:
        res = await a.next()
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.PREVIOUS:
        res = await a.previous()
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.VOLUME_UP:
        res = await a.volume_up()
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.VOLUME_DOWN:
        res = await a.volume_down()
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.MUTE_TOGGLE:
        res = await a.mute(not configured_entity.attributes[media_player.Attributes.MUTED])
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.ON:
        res = await a.power_on()
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.OFF:
        res = await a.power_off()
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.SELECT_SOURCE:
        res = await a.set_input(params["source"])
        await api.acknowledge_command(
            websocket, req_id, ucapi.StatusCodes.OK if res is True else ucapi.StatusCodes.SERVER_ERROR
        )


def _key_update_helper(key: str, value: str | None, attributes, configured_entity):
    if value is None:
        return attributes

    if key in configured_entity.attributes:
        if configured_entity.attributes[key] != value:
            attributes[key] = value
    else:
        attributes[key] = value

    return attributes


async def _handle_connected(avr_id: str):
    _LOG.debug("AVR connected: %s", avr_id)

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


async def _handle_disconnected(avr_id: str):
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


async def _handle_connection_error(avr_id: str, message):
    _LOG.error(message)

    for entity_id in _entities_from_avr(avr_id):
        configured_entity = api.configured_entities.get(entity_id)
        if configured_entity is None:
            continue

        if configured_entity.entity_type == ucapi.EntityTypes.MEDIA_PLAYER:
            api.configured_entities.update_attributes(
                entity_id, {media_player.Attributes.STATE: media_player.States.UNAVAILABLE}
            )


async def _handle_avr_update(avr_id: str, update):
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

    # if "position" in update:
    #     attributes = keyUpdateHelper(media_player.Attributes.MEDIA_POSITION, update["position"], attributes,
    #                                  configuredEntity)
    if "artwork" in update:
        attributes[media_player.Attributes.MEDIA_IMAGE_URL] = update["artwork"]
    # if "total_time" in update:
    #     attributes = keyUpdateHelper(media_player.Attributes.MEDIA_DURATION, update["total_time"],
    #                                  attributes, configuredEntity)
    if "title" in update:
        attributes = _key_update_helper(
            media_player.Attributes.MEDIA_TITLE, update["title"], attributes, configured_entity
        )
    if "artist" in update:
        attributes = _key_update_helper(
            media_player.Attributes.MEDIA_ARTIST, update["artist"], attributes, configured_entity
        )
    if "album" in update:
        attributes = _key_update_helper(
            media_player.Attributes.MEDIA_ALBUM, update["album"], attributes, configured_entity
        )
    if "source" in update:
        attributes = _key_update_helper(media_player.Attributes.SOURCE, update["source"], attributes, configured_entity)
    if "sourceList" in update:
        if media_player.Attributes.SOURCE_LIST in configured_entity.attributes:
            if len(configured_entity.attributes[media_player.Attributes.SOURCE_LIST]) != len(update["sourceList"]):
                attributes[media_player.Attributes.SOURCE_LIST] = update["sourceList"]
        else:
            attributes[media_player.Attributes.SOURCE_LIST] = update["sourceList"]
    if "volume" in update:
        attributes[media_player.Attributes.VOLUME] = update["volume"]

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


def _add_available_entity(avr_id: str, name):
    # plain and simple for now: only one media_player per AVR device
    entity = media_player.MediaPlayer(
        _create_entity_id(avr_id, ucapi.EntityTypes.MEDIA_PLAYER),
        name,
        [
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
        ],
        {
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
        },
        device_class=media_player.DeviceClasses.RECEIVER,
    )

    api.available_entities.add(entity)


def _create_entity_id(avr_id: str, entity_type: ucapi.EntityTypes) -> str:
    return f"{entity_type.value}.{avr_id}"


async def main():
    """Start the Remote Two integration driver."""
    global _CFG_FILE_PATH

    logging.basicConfig()

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("avr").setLevel(level)
    logging.getLogger("driver").setLevel(level)

    path = api.config_dir_path
    _CFG_FILE_PATH = os.path.join(path, _CFG_FILENAME)

    res = await load_config()

    if res is True:
        for item in _config:
            _configured_avrs[item["id"]] = avr.DenonAVR(_LOOP, item["ipaddress"])
            await _configured_avrs[item["id"]].connect()
            _add_available_entity(item["id"], _configured_avrs[item["id"]].name)
    else:
        _LOG.error("Cannot load config")

    await api.init("driver.json")


if __name__ == "__main__":
    _LOOP.run_until_complete(main())
    _LOOP.run_forever()
