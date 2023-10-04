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
dataPath = None
api = uc.IntegrationAPI(LOOP)
config = []
configuredAVRs = {}
    
async def clearConfig():
    """"Remove the configuration file"""
    global config
    config = []

    if os.path.exists(dataPath + '/config.json'):
        os.remove(dataPath + '/config.json')

async def storeCofig():
    global config
    f = None
    try:
        f= open(dataPath + '/config.json', 'w+', encoding='utf-8')
    except OSError:
        LOG.error('Cannot write the config file')
        return

    json.dump(config, f, ensure_ascii=False)

    f.close()

async def loadConfig():
    """"Load the config into the config global variable"""
    global config
    f = None
    try:
        f = open(dataPath + '/config.json', 'r', encoding='utf-8')
    except OSError:
        LOG.error('Cannot open the config file')
    
    if f is None:
        return False

    try:
        data = json.load(f)
        f.close()
    except ValueError:
        LOG.error('Empty config file')
        return False

    config = data

    if not config:
        return False

    return True
        

# DRIVER SETUP
@api.events.on(uc.uc.EVENTS.SETUP_DRIVER)
async def event_handler(websocket, id, data):
    LOG.debug('Starting driver setup')
    await clearConfig()
    await api.acknowledgeCommand(websocket, id)
    await api.driverSetupProgress(websocket)

    LOG.debug('Starting discovery')
    avrs = await avr.discoverDenonAVRs();
    dropdownItems = []

    LOG.debug(avrs)

    for a in avrs:
        tvData = {
            'id': a["ipaddress"],
            'label': {
                'en': a["name"] + " " + a["manufacturer"] + " " + a["model"]
            }
        }

        dropdownItems.append(tvData)

    if not dropdownItems:
        LOG.warning('No AVRs found')
        await api.driverSetupError(websocket)
        # TODO START AGAIN
        return

    await api.requestDriverSetupUserInput(websocket, 'Please choose your Denon AVR', [
        { 
        'field': { 
            'dropdown': {
                'value': dropdownItems[0]['id'],
                'items': dropdownItems
            }
        },
        'id': 'choice',
        'label': { 'en': 'Choose your Denon AVR' }
        }
    ])

@api.events.on(uc.uc.EVENTS.SETUP_DRIVER_USER_DATA)
async def event_handler(websocket, id, data):
    global configuredAVRs
    global config

    await api.acknowledgeCommand(websocket, id)
    await api.driverSetupProgress(websocket)

    if "choice" in data:
        choice = data['choice']
        LOG.debug('Chosen Denon AVR: ' + choice)

        obj = avr.DenonAVR(LOOP, choice)
        await obj.connect()
        configuredAVRs[obj.id] = obj

        addAvailableEntity(obj.id, obj.name)
        
        config.append({
            "id": obj.id,
            "name": obj.name,
            "ipaddress": obj.ipaddress
        })
        await storeCofig()

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
async def event_handler(entityIds):
    global configuredAVRs

    for entityId in entityIds:
        if entityId in configuredAVRs:
            LOG.debug('We have a match, start listening to events')
            a = configuredAVRs[entityId]

            @a.events.on(avr.EVENTS.CONNECTED)
            async def _onConnected(identifier):
                await handleConnected(identifier)

            @a.events.on(avr.EVENTS.DISCONNECTED)
            async def _onDisconnected(identifier):
                await handleDisconnected(identifier)
            
            @a.events.on(avr.EVENTS.ERROR)
            async def _onDisconnected(identifier, message):
                await handleConnectionError(identifier, message)

            @a.events.on(avr.EVENTS.UPDATE)
            async def onUpdate(update):
                await handleAVRUpdate(entityId, update)

            await a.connect()

            api.configuredEntities.updateEntityAttributes(entityId, {
                entities.media_player.ATTRIBUTES.STATE: entities.media_player.STATES.ON if a.state == avr.STATES.ON else entities.media_player.STATES.OFF,
                entities.media_player.ATTRIBUTES.SOURCE_LIST: a.input_list,
                entities.media_player.ATTRIBUTES.SOURCE: a.input,
                entities.media_player.ATTRIBUTES.VOLUME: a.volume,
                entities.media_player.ATTRIBUTES.MEDIA_ARTIST: a.artist,
                entities.media_player.ATTRIBUTES.MEDIA_TITLE: a.title,
                entities.media_player.ATTRIBUTES.MEDIA_IMAGE_URL: a.artwork,
            })

# On unsubscribe, we disconnect the objects and remove listeners for events
@api.events.on(uc.uc.EVENTS.UNSUBSCRIBE_ENTITIES)
async def event_handler(entityIds):
    global configuredAVRs

    for entityId in entityIds:
        if entityId in configuredAVRs:
            LOG.debug('We have a match, stop listening to events')
            a = configuredAVRs[entityId]
            a.events.remove_all_listeners()
            await a.disconnect()

# We handle commands here
@api.events.on(uc.uc.EVENTS.ENTITY_COMMAND)
async def event_handler(websocket, id, entityId, entityType, cmdId, params):
    global configuredAVRs
 
    a = configuredAVRs[entityId]
    configuredEntity = api.configuredEntities.getEntity(entityId)

    if cmdId == entities.media_player.COMMANDS.PLAY_PAUSE:
        res = await a.playPause()
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmdId == entities.media_player.COMMANDS.NEXT:
        res = await a.next()
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmdId == entities.media_player.COMMANDS.PREVIOUS:
        res = await a.previous()
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmdId == entities.media_player.COMMANDS.VOLUME_UP:
        res = await a.volumeUp()
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmdId == entities.media_player.COMMANDS.VOLUME_DOWN:
        res = await a.volumeDown()
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmdId == entities.media_player.COMMANDS.MUTE_TOGGLE:
        res = await a.mute(not configuredEntity.attributes[entities.media_player.ATTRIBUTES.MUTED])
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmdId == entities.media_player.COMMANDS.ON:
        res = await a.powerOn()
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmdId == entities.media_player.COMMANDS.OFF:
        res = await a.powerOff()
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)
    elif cmdId == entities.media_player.COMMANDS.SELECT_SOURCE:
        res = await a.setInput(params["source"])
        await api.acknowledgeCommand(websocket, id, uc.uc.STATUS_CODES.OK if res is True else uc.uc.STATUS_CODES.SERVER_ERROR)


def keyUpdateHelper(key, value, attributes, configuredEntity):
    if value is None:
        return attributes

    if key in configuredEntity.attributes:
        if configuredEntity.attributes[key] != value:
            attributes[key] = value
    else:
        attributes[key] = value

    return attributes


async def handleConnected(identifier):
    LOG.debug('AVR connected: %s', identifier)
    configuredEntity = api.configuredEntities.getEntity(identifier)

    if configuredEntity.attributes[entities.media_player.ATTRIBUTES.STATE] == entities.media_player.STATES.UNAVAILABLE:
        api.configuredEntities.updateEntityAttributes(identifier, {
            entities.media_player.ATTRIBUTES.STATE: entities.media_player.STATES.STANDBY
        })


async def handleDisconnected(identifier):
    LOG.debug('AVR disconnected: %s', identifier)
    api.configuredEntities.updateEntityAttributes(identifier, {
        entities.media_player.ATTRIBUTES.STATE: entities.media_player.STATES.STANDBY
    })


async def handleConnectionError(identifier, message):
    LOG.error(message)
    api.configuredEntities.updateEntityAttributes(identifier, {
        entities.media_player.ATTRIBUTES.STATE: entities.media_player.STATES.UNAVAILABLE
    })


async def handleAVRUpdate(entityId, update):
    attributes = {}

    configuredEntity = api.configuredEntities.getEntity(entityId)

    LOG.debug(update)

    if 'state' in update:
        state = entities.media_player.STATES.UNKNOWN

        if update['state'] == avr.STATES.ON:
            state = entities.media_player.STATES.ON
        elif update['state'] == avr.STATES.PLAYING:
            state = entities.media_player.STATES.PLAYING
        elif update['state'] == avr.STATES.PAUSED:
            state = entities.media_player.STATES.PAUSED
            state = entities.media_player.STATES.PAUSED
        elif update['state'] == avr.STATES.OFF:
            state = entities.media_player.STATES.OFF

        attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.STATE, state, attributes, configuredEntity)

    # if 'position' in update:
    #     attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.MEDIA_POSITION, update['position'], attributes, configuredEntity)
    if 'artwork' in update:
        attributes[entities.media_player.ATTRIBUTES.MEDIA_IMAGE_URL] = update['artwork']
    # if 'total_time' in update:
    #     attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.MEDIA_DURATION, update['total_time'], attributes, configuredEntity)
    if 'title' in update:
        attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.MEDIA_TITLE, update['title'], attributes, configuredEntity)
    if 'artist' in update:
        attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.MEDIA_ARTIST, update['artist'], attributes, configuredEntity)
    if 'album' in update:
        attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.MEDIA_ALBUM, update['album'], attributes, configuredEntity)
    if 'source' in update:
        attributes = keyUpdateHelper(entities.media_player.ATTRIBUTES.SOURCE, update['source'], attributes, configuredEntity)
    if 'sourceList' in update:
        if entities.media_player.ATTRIBUTES.SOURCE_LIST in configuredEntity.attributes:
            if len(configuredEntity.attributes[entities.media_player.ATTRIBUTES.SOURCE_LIST]) != len(update['sourceList']):
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
            attributes[entities.media_player.ATTRIBUTES.SOURCE] = ""
            # attributes[entities.media_player.ATTRIBUTES.MEDIA_DURATION] = 0

    if attributes:
        api.configuredEntities.updateEntityAttributes(entityId, attributes)


def addAvailableEntity(identifier, name):
    entity = entities.media_player.MediaPlayer(identifier, name, [
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
    ], {
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
    }, deviceClass = entities.media_player.DEVICECLASSES.RECEIVER)

    api.availableEntities.addEntity(entity)


async def main():
    global dataPath
    global config

    dataPath = api.configDirPath
    res = await loadConfig()

    if res is True:
        for item in config:
            configuredAVRs[item["id"]] = avr.DenonAVR(LOOP, item["ipaddress"])
            await configuredAVRs[item["id"]].connect()
            addAvailableEntity(item['id'], configuredAVRs[item["id"]].name)
    else:  
        LOG.error("Cannot load config")

    await api.init('driver.json')

if __name__ == "__main__":
    LOOP.run_until_complete(main())
    LOOP.run_forever()
