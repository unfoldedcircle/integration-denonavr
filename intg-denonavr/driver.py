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
import ucapi.api as uc
import ucapi.api_definitions as api_def
from ucapi import media_player

_LOG = logging.getLogger("driver")  # avoid having __main__ in log messages
LOOP = asyncio.get_event_loop()

CFG_FILENAME = "config.json"
# Global variables
CFG_FILE_PATH: str | None = None
api = uc.IntegrationAPI(LOOP)
config: list[dict[str, any]] = []
configured_avrs: dict[str, avr.DenonAVR] = {}


async def clear_config():
    """Remove the configuration file."""
    global config
    config = []

    if os.path.exists(CFG_FILE_PATH):
        os.remove(CFG_FILE_PATH)


async def store_config() -> bool:
    """
    Store the configuration file.

    :return: True if the configuration could be saved.
    """
    try:
        with open(CFG_FILE_PATH, "w+", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False)
        return True
    except OSError:
        _LOG.error("Cannot write the config file")

    return False


async def load_config():
    """
    Load the config into the config global variable.

    :return: True if the configuration could be loaded.
    """
    global config

    try:
        with open(CFG_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = data
        return True
    except OSError:
        _LOG.error("Cannot open the config file")
    except ValueError:
        _LOG.error("Empty or invalid config file")

    return False


# DRIVER SETUP
@api.events.on(api_def.Events.SETUP_DRIVER)
async def _on_setup_driver(websocket, req_id, _data):
    _LOG.debug("Starting driver setup")
    await clear_config()
    await api.acknowledge_command(websocket, req_id)
    await api.driver_setup_progress(websocket)

    _LOG.debug("Starting discovery")
    avrs = await avr.discover_denon_avrs()
    dropdown_items = []

    for a in avrs:
        tv_data = {"id": a["host"], "label": {"en": f"{a['friendlyName']} ({a['modelName']}) [{a['host']}]"}}
        dropdown_items.append(tv_data)

    if not dropdown_items:
        _LOG.warning("No AVRs found")
        await api.driver_setup_error(websocket)
        return

    await api.request_driver_setup_user_input(
        websocket,
        "Please choose your Denon AVR",
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


@api.events.on(api_def.Events.SETUP_DRIVER_USER_DATA)
async def _on_setup_driver_user_data(websocket, req_id, data):
    await api.acknowledge_command(websocket, req_id)
    await api.driver_setup_progress(websocket)

    if "choice" in data:
        choice = data["choice"]
        _LOG.debug("Chosen Denon AVR: %s", choice)

        obj = avr.DenonAVR(LOOP, choice)
        # FIXME handle connect error!
        await obj.connect()
        configured_avrs[obj.id] = obj

        _add_available_entity(obj.id, obj.name)

        config.append({"id": obj.id, "name": obj.name, "ipaddress": obj.ipaddress})
        await store_config()

        await api.driver_setup_complete(websocket)
    else:
        _LOG.error("No choice was received")
        await api.driver_setup_error(websocket)


# When the core connects, we just set the device state
@api.events.on(api_def.Events.CONNECT)
async def _on_connect():
    await api.set_device_state(api_def.DeviceStates.CONNECTED)


# When the core disconnects, we just set the device state
@api.events.on(api_def.Events.DISCONNECT)
async def _on_disconnect():
    _LOG.debug("Client disconnected, disconnecting all AVRs")
    for configured in configured_avrs.values():
        configured.events.remove_all_listeners()
        await configured.disconnect()

    await api.set_device_state(api_def.DeviceStates.DISCONNECTED)


# On standby, we disconnect every Denon AVR objects
@api.events.on(api_def.Events.ENTER_STANDBY)
async def _on_enter_standby():
    for configured in configured_avrs.values():
        await configured.disconnect()


# On exit standby we wait a bit then connect all Denon AVR objects
@api.events.on(api_def.Events.EXIT_STANDBY)
async def _on_exit_standby():
    await asyncio.sleep(2)

    for configured in configured_avrs.values():
        await configured.connect()


# When the core subscribes to entities, we set these to UNAVAILABLE state
# then we hook up to the signals of the object and then connect
@api.events.on(api_def.Events.SUBSCRIBE_ENTITIES)
async def _on_subscribe_entities(entity_ids):
    # TODO verify if this is correct: pylint complains about `entity_id` and `a` being cell-var-from-loop
    # https://pylint.readthedocs.io/en/latest/user_guide/messages/warning/cell-var-from-loop.html
    for entity_id in entity_ids:
        if entity_id in configured_avrs:
            _LOG.debug("We have a match, start listening to events")
            a = configured_avrs[entity_id]

            @a.events.on(avr.Events.CONNECTED)
            async def on_connected(identifier):
                await _handle_connected(identifier)

            @a.events.on(avr.Events.DISCONNECTED)
            async def on_disconnected(identifier):
                await _handle_disconnected(identifier)

            @a.events.on(avr.Events.ERROR)
            async def on_error(identifier, message):
                await _handle_connection_error(identifier, message)

            @a.events.on(avr.Events.UPDATE)
            async def on_update(update):
                # FIXME W0640: Cell variable entity_id defined in loop (cell-var-from-loop)
                #       This is most likely the WRONG entity_id if we have MULTIPLE configuredAVRs
                await _handle_avr_update(entity_id, update)

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
@api.events.on(api_def.Events.UNSUBSCRIBE_ENTITIES)
async def _on_unsubscribe_entities(entity_ids):
    for entity_id in entity_ids:
        if entity_id in configured_avrs:
            _LOG.debug("We have a match, stop listening to events")
            a = configured_avrs[entity_id]
            a.events.remove_all_listeners()
            await a.disconnect()


# We handle commands here
@api.events.on(api_def.Events.ENTITY_COMMAND)
async def _on_entity_command(websocket, req_id, entity_id, _entity_type, cmd_id, params):
    a = configured_avrs[entity_id]
    configured_entity = api.configured_entities.get(entity_id)

    if cmd_id == media_player.Commands.PLAY_PAUSE:
        res = await a.play_pause()
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.NEXT:
        res = await a.next()
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.PREVIOUS:
        res = await a.previous()
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.VOLUME_UP:
        res = await a.volume_up()
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.VOLUME_DOWN:
        res = await a.volume_down()
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.MUTE_TOGGLE:
        res = await a.mute(not configured_entity.attributes[media_player.Attributes.MUTED])
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.ON:
        res = await a.power_on()
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.OFF:
        res = await a.power_off()
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )
    elif cmd_id == media_player.Commands.SELECT_SOURCE:
        res = await a.set_input(params["source"])
        await api.acknowledge_command(
            websocket, req_id, api_def.StatusCodes.OK if res is True else api_def.StatusCodes.SERVER_ERROR
        )


def _key_update_helper(key, value, attributes, configured_entity):
    if value is None:
        return attributes

    if key in configured_entity.attributes:
        if configured_entity.attributes[key] != value:
            attributes[key] = value
    else:
        attributes[key] = value

    return attributes


async def _handle_connected(identifier):
    _LOG.debug("AVR connected: %s", identifier)
    configured_entity = api.configured_entities.get(identifier)

    if configured_entity.attributes[media_player.Attributes.STATE] == media_player.States.UNAVAILABLE:
        api.configured_entities.update_attributes(
            identifier, {media_player.Attributes.STATE: media_player.States.STANDBY}
        )


async def _handle_disconnected(identifier):
    _LOG.debug("AVR disconnected: %s", identifier)
    api.configured_entities.update_attributes(identifier, {media_player.Attributes.STATE: media_player.States.STANDBY})


async def _handle_connection_error(identifier, message):
    _LOG.error(message)
    api.configured_entities.update_attributes(
        identifier, {media_player.Attributes.STATE: media_player.States.UNAVAILABLE}
    )


async def _handle_avr_update(entity_id, update):
    attributes = {}

    configured_entity = api.configured_entities.get(entity_id)

    _LOG.debug("AVR update: %s", update)

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

    _update_attributes(attributes)

    if attributes:
        api.configured_entities.update_attributes(entity_id, attributes)


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


def _update_attributes(attributes):
    """
    Update the entity attributes based on the state.

    :param attributes: entity attributes dictionary
    """
    if media_player.Attributes.STATE in attributes:
        if attributes[media_player.Attributes.STATE] == media_player.States.OFF:
            attributes[media_player.Attributes.MEDIA_IMAGE_URL] = ""
            attributes[media_player.Attributes.MEDIA_ALBUM] = ""
            attributes[media_player.Attributes.MEDIA_ARTIST] = ""
            attributes[media_player.Attributes.MEDIA_TITLE] = ""
            attributes[media_player.Attributes.MEDIA_TYPE] = ""
            attributes[media_player.Attributes.SOURCE] = ""
            # attributes[media_player.Attributes.MEDIA_DURATION] = 0


def _add_available_entity(identifier, name):
    entity = media_player.MediaPlayer(
        identifier,
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


async def main():
    """Start the Remote Two integration driver."""
    global CFG_FILE_PATH

    logging.basicConfig()

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()
    logging.getLogger("avr").setLevel(level)
    logging.getLogger("driver").setLevel(level)

    path = api.config_dir_path
    CFG_FILE_PATH = os.path.join(path, CFG_FILENAME)

    res = await load_config()

    if res is True:
        for item in config:
            configured_avrs[item["id"]] = avr.DenonAVR(LOOP, item["ipaddress"])
            await configured_avrs[item["id"]].connect()
            _add_available_entity(item["id"], configured_avrs[item["id"]].name)
    else:
        _LOG.error("Cannot load config")

    await api.init("driver.json")


if __name__ == "__main__":
    LOOP.run_until_complete(main())
    LOOP.run_forever()
