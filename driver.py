import asyncio
import logging
import json
import os

import ucapi.api as uc
import ucapi.entities as entities

import avr

LOG = logging.getLogger(__name__)
LOOP = asyncio.get_event_loop()
LOG.setLevel(logging.DEBUG)

# Global variables
cfg_file_path = "config.json"
api = uc.IntegrationAPI(LOOP)
config = []
configuredAVRs = {}


async def clear_config():
    """"Remove the configuration file"""
    global config
    config = []

    if os.path.exists(cfg_file_path):
        os.remove(cfg_file_path)


async def store_config():
    global config

    try:
        f = open(cfg_file_path, 'w+', encoding='utf-8')
        json.dump(config, f, ensure_ascii=False)

        f.close()
        return True
    except OSError:
        LOG.error('Cannot write the config file')

    return False


async def load_config():
    """"Load the config into the config global variable"""
    global config

    try:
        f = open(cfg_file_path, 'r', encoding='utf-8')
        data = json.load(f)
        f.close()
        config = data
        return True
    except OSError:
        LOG.error('Cannot open the config file')
    except ValueError:
        LOG.error('Empty or invalid config file')

    return False


# DRIVER SETUP
@api.events.on(uc.uc.EVENTS.SETUP_DRIVER)
async def event_handler(websocket, req_id, _data):
    LOG.debug('Starting driver setup')
    await clear_config()
    await api.acknowledgeCommand(websocket, req_id)
    await api.driverSetupProgress(websocket)

    LOG.debug('Starting discovery')
    avrs = await avr.discover_denon_avrs()
    dropdown_items = []

    LOG.debug(avrs)

    for a in avrs:
        tv_data = {'id': a["ipaddress"], 'label': {'en': a["name"] + " " + a["manufacturer"] + " " + a["model"]}}

        dropdown_items.append(tv_data)

    if not dropdown_items:
        LOG.warning('No AVRs found')
        await api.driverSetupError(websocket)
        # TODO START AGAIN
        return

    await api.requestDriverSetupUserInput(
        websocket,
        'Please choose your Denon AVR',
        [
            {
                'field': {
                    'dropdown': {
                        'value': dropdown_items[0]['id'],
                        'items': dropdown_items
                    }
                },
                'id': 'choice',
                'label': {'en': 'Choose your Denon AVR'}
            }
        ]
    )


@api.events.on(uc.uc.EVENTS.SETUP_DRIVER_USER_DATA)
async def event_handler(websocket, req_id, data):
    global configuredAVRs
    global config

    await api.acknowledgeCommand(websocket, req_id)
    await api.driverSetupProgress(websocket)

    if "choice" in data:
        choice = data['choice']
        LOG.debug('Chosen Denon AVR: ' + choice)

        obj = avr.DenonAVR(LOOP, choice)
        # FIXME handle connect error!
        await obj.connect()
        configuredAVRs[obj.id] = obj

        add_available_entity(obj.id, obj.name)

        config.append({"id": obj.id, "name": obj.name, "ipaddress": obj.ipaddress})
        await store_config()

        await api.driverSetupComplete(websocket)
    else:
        LOG.error('No choice was received')
        await api.driverSetupError(websocket)


# When the core connects, we just set the device state
@api.events.on(uc.uc.EVENTS.CONNECT)
async def event_handler():
    await api.setDeviceState(uc.uc.DEVICE_STATES.CONNECTED)


# When the core disconnects, we just set the device state
@api.events.on(uc.uc.EVENTS.DISCONNECT)
async def event_handler():
    for entityId in configuredAVRs:
        LOG.debug('Client disconnected, disconnecting all AVRs')
        a = configuredAVRs[entityId]
        a.events.remove_all_listeners()
        await a.disconnect()

    await api.setDeviceState(uc.uc.DEVICE_STATES.DISCONNECTED)


# On standby, we disconnect every Denon AVR objects
@api.events.on(uc.uc.EVENTS.ENTER_STANDBY)
async def event_handler():
    global configuredAVRs

    for a in configuredAVRs:
        await configuredAVRs[a].disconnect()


# On exit standby we wait a bit then connect all Denon AVR objects
@api.events.on(uc.uc.EVENTS.EXIT_STANDBY)
async def event_handler():
    global configuredAVRs

    await asyncio.sleep(2)

    for a in configuredAVRs:
        await configuredAVRs[a].connect()


# When the core subscribes to entities, we set these to UNAVAILABLE state
# then we hook up to the signals of the object and then connect
@api.events.on(uc.uc.EVENTS.SUBSCRIBE_ENTITIES)
async def event_handler(entity_ids):
    global configuredAVRs

    for entityId in entity_ids:
        if entityId in configuredAVRs:
            LOG.debug('We have a match, start listening to events')
            a = configuredAVRs[entityId]

            @a.events.on(avr.EVENTS.CONNECTED)
            async def _on_connected(identifier):
                await handle_connected(identifier)

            @a.events.on(avr.EVENTS.DISCONNECTED)
            async def _on_disconnected(identifier):
                await handle_disconnected(identifier)

            @a.events.on(avr.EVENTS.ERROR)
            async def _on_disconnected(identifier, message):
                await handle_connection_error(identifier, message)

            @a.events.on(avr.EVENTS.UPDATE)
            async def on_update(update):
                await handle_avr_update(entityId, update)

            await a.connect()

            api.configuredEntities.updateEntityAttributes(entityId, {
                entities.media_player.ATTRIBUTES.STATE:
                    entities.media_player.STATES.ON if a.state == avr.STATES.ON else entities.media_player.STATES.OFF,
                entities.media_player.ATTRIBUTES.SOURCE_LIST: a.input_list,
                entities.media_player.ATTRIBUTES.SOURCE: a.input, entities.media_player.ATTRIBUTES.VOLUME: a.volume,
                entities.media_player.ATTRIBUTES.MEDIA_ARTIST: a.artist,
                entities.media_player.ATTRIBUTES.MEDIA_TITLE: a.title,
                entities.media_player.ATTRIBUTES.MEDIA_IMAGE_URL: a.artwork, })


# On unsubscribe, we disconnect the objects and remove listeners for events
@api.events.on(uc.uc.EVENTS.UNSUBSCRIBE_ENTITIES)
async def event_handler(entity_ids):
    global configuredAVRs

    for entityId in entity_ids:
        if entityId in configuredAVRs:
            LOG.debug('We have a match, stop listening to events')
            a = configuredAVRs[entityId]
            a.events.remove_all_listeners()
            await a.disconnect()


# We handle commands here
@api.events.on(uc.uc.EVENTS.ENTITY_COMMAND)
async def event_handler(websocket, req_id, entity_id, _entity_type, cmd_id, params):
    global configuredAVRs

    a = configuredAVRs[entity_id]
    configured_entity = api.configuredEntities.getEntity(entity_id)

    if cmd_id == entities.media_player.COMMANDS.PLAY_PAUSE:
        res = await a.play_pause()
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmd_id == entities.media_player.COMMANDS.NEXT:
        res = await a.next()
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmd_id == entities.media_player.COMMANDS.PREVIOUS:
        res = await a.previous()
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmd_id == entities.media_player.COMMANDS.VOLUME_UP:
        res = await a.volume_up()
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmd_id == entities.media_player.COMMANDS.VOLUME_DOWN:
        res = await a.volume_down()
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmd_id == entities.media_player.COMMANDS.MUTE_TOGGLE:
        res = await a.mute(not configured_entity.attributes[entities.media_player.ATTRIBUTES.MUTED])
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmd_id == entities.media_player.COMMANDS.ON:
        res = await a.power_on()
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmd_id == entities.media_player.COMMANDS.OFF:
        res = await a.power_off()
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmd_id == entities.media_player.COMMANDS.SELECT_SOURCE:
        res = await a.set_input(params["source"])
        await api.acknowledgeCommand(websocket, req_id,
                                     uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)


def key_update_helper(key, value, attributes, configured_entity):
    if value is None:
        return attributes

    if key in configured_entity.attributes:
        if configured_entity.attributes[key] != value:
            attributes[key] = value
    else:
        attributes[key] = value

    return attributes


async def handle_connected(identifier):
    LOG.debug('AVR connected: %s', identifier)
    configured_entity = api.configuredEntities.getEntity(identifier)

    if configured_entity.attributes[entities.media_player.ATTRIBUTES.STATE] == entities.media_player.STATES.UNAVAILABLE:
        api.configuredEntities.updateEntityAttributes(identifier, {
            entities.media_player.ATTRIBUTES.STATE: entities.media_player.STATES.STANDBY})


async def handle_disconnected(identifier):
    LOG.debug('AVR disconnected: %s', identifier)
    api.configuredEntities.updateEntityAttributes(identifier, {
        entities.media_player.ATTRIBUTES.STATE: entities.media_player.STATES.STANDBY})


async def handle_connection_error(identifier, message):
    LOG.error(message)
    api.configuredEntities.updateEntityAttributes(identifier, {
        entities.media_player.ATTRIBUTES.STATE: entities.media_player.STATES.UNAVAILABLE})


async def handle_avr_update(entity_id, update):
    attributes = {}

    configured_entity = api.configuredEntities.getEntity(entity_id)

    LOG.debug(update)

    if 'state' in update:
        state = entities.media_player.STATES.UNKNOWN

        if update['state'] == avr.STATES.ON:
            state = entities.media_player.STATES.ON
        elif update['state'] == avr.STATES.PLAYING:
            state = entities.media_player.STATES.PLAYING
        elif update['state'] == avr.STATES.PAUSED:
            state = entities.media_player.STATES.PAUSED
        elif update['state'] == avr.STATES.OFF:
            state = entities.media_player.STATES.OFF

        attributes = key_update_helper(entities.media_player.ATTRIBUTES.STATE, state, attributes, configured_entity)

    # if 'position' in update:
    #     attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.MEDIA_POSITION, update['position'], attributes,
    #                                  configuredEntity)
    if 'artwork' in update:
        attributes[entities.media_player.ATTRIBUTES.MEDIA_IMAGE_URL] = update['artwork']
    # if 'total_time' in update:
    #     attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.MEDIA_DURATION, update['total_time'],
    #                                  attributes, configuredEntity)
    if 'title' in update:
        attributes = key_update_helper(entities.media_player.ATTRIBUTES.MEDIA_TITLE, update['title'], attributes,
                                       configured_entity)
    if 'artist' in update:
        attributes = key_update_helper(entities.media_player.ATTRIBUTES.MEDIA_ARTIST, update['artist'], attributes,
                                       configured_entity)
    if 'album' in update:
        attributes = key_update_helper(entities.media_player.ATTRIBUTES.MEDIA_ALBUM, update['album'], attributes,
                                       configured_entity)
    if 'source' in update:
        attributes = key_update_helper(entities.media_player.ATTRIBUTES.SOURCE, update['source'], attributes,
                                       configured_entity)
    if 'sourceList' in update:
        if entities.media_player.ATTRIBUTES.SOURCE_LIST in configured_entity.attributes:
            if len(configured_entity.attributes[entities.media_player.ATTRIBUTES.SOURCE_LIST]) != len(
                    update['sourceList']):
                attributes[entities.media_player.ATTRIBUTES.SOURCE_LIST] = update['sourceList']
        else:
            attributes[entities.media_player.ATTRIBUTES.SOURCE_LIST] = update['sourceList']
    if 'volume' in update:
        attributes[entities.media_player.ATTRIBUTES.VOLUME] = update['volume']

    if entities.media_player.ATTRIBUTES.STATE in attributes:
        if attributes[entities.media_player.ATTRIBUTES.STATE] == entities.media_player.STATES.OFF:
            attributes[entities.media_player.ATTRIBUTES.MEDIA_IMAGE_URL] = ""
            attributes[entities.media_player.ATTRIBUTES.MEDIA_ALBUM] = ""
            attributes[entities.media_player.ATTRIBUTES.MEDIA_ARTIST] = ""
            attributes[entities.media_player.ATTRIBUTES.MEDIA_TITLE] = ""
            attributes[entities.media_player.ATTRIBUTES.MEDIA_TYPE] = ""
            attributes[
                entities.media_player.ATTRIBUTES.SOURCE] = ""
            # attributes[entities.media_player.ATTRIBUTES.MEDIA_DURATION] = 0

    if attributes:
        api.configuredEntities.updateEntityAttributes(entity_id, attributes)


def add_available_entity(identifier, name):
    entity = entities.media_player.MediaPlayer(
        identifier,
        name,
        [
            entities.media_player.FEATURES.ON_OFF,
            entities.media_player.FEATURES.VOLUME,
            entities.media_player.FEATURES.VOLUME_UP_DOWN,
            entities.media_player.FEATURES.MUTE_TOGGLE,
            entities.media_player.FEATURES.PLAY_PAUSE,
            entities.media_player.FEATURES.NEXT,
            entities.media_player.FEATURES.PREVIOUS,
            # entities.media_player.FEATURES.MEDIA_DURATION,
            # entities.media_player.FEATURES.MEDIA_POSITION,
            entities.media_player.FEATURES.MEDIA_TITLE,
            entities.media_player.FEATURES.MEDIA_ARTIST,
            entities.media_player.FEATURES.MEDIA_ALBUM,
            entities.media_player.FEATURES.MEDIA_IMAGE_URL,
            entities.media_player.FEATURES.MEDIA_TYPE,
            entities.media_player.FEATURES.SELECT_SOURCE
        ],
        {
            entities.media_player.ATTRIBUTES.STATE: entities.media_player.STATES.UNAVAILABLE,
            entities.media_player.ATTRIBUTES.VOLUME: 0,
            entities.media_player.ATTRIBUTES.MUTED: False,
            # entities.media_player.ATTRIBUTES.MEDIA_DURATION: 0,
            # entities.media_player.ATTRIBUTES.MEDIA_POSITION: 0,
            entities.media_player.ATTRIBUTES.MEDIA_IMAGE_URL: "",
            entities.media_player.ATTRIBUTES.MEDIA_TITLE: "",
            entities.media_player.ATTRIBUTES.MEDIA_ARTIST: "",
            entities.media_player.ATTRIBUTES.MEDIA_ALBUM: "",
            entities.media_player.ATTRIBUTES.SOURCE: ""
        },
        deviceClass=entities.media_player.DEVICECLASSES.RECEIVER)

    api.availableEntities.addEntity(entity)


async def main():
    global cfg_file_path
    global config

    path = api.configDirPath
    cfg_file_path = os.path.join(path, cfg_file_path)

    res = await load_config()

    if res is True:
        for item in config:
            configuredAVRs[item["id"]] = avr.DenonAVR(LOOP, item["ipaddress"])
            await configuredAVRs[item["id"]].connect()
            add_available_entity(item['id'], configuredAVRs[item["id"]].name)
    else:
        LOG.error("Cannot load config")

    await api.init('driver.json')


if __name__ == "__main__":
    LOOP.run_until_complete(main())
    LOOP.run_forever()
