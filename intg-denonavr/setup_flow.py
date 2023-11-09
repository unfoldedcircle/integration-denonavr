"""Setup flow for Denon AVR integration."""

import asyncio
import logging
from enum import IntEnum

import avr
import config
from config import AvrDevice
from ucapi import (
    AbortDriverSetup,
    DriverSetupRequest,
    IntegrationSetupError,
    RequestUserInput,
    SetupAction,
    SetupComplete,
    SetupDriver,
    SetupError,
    UserDataResponse,
)

_LOG = logging.getLogger(__name__)


class SetupSteps(IntEnum):
    """Enumeration of setup steps to keep track of user data responses."""

    INIT = 0
    DEVICE_CHOICE = 1


_setup_step = SetupSteps.INIT


async def driver_setup_handler(msg: SetupDriver) -> SetupAction:
    """
    Dispatch driver setup requests to corresponding handlers.

    Either start the setup process or handle the selected AVR device.

    :param msg: the setup driver request object, either DriverSetupRequest or UserDataResponse
    :return: the setup action on how to continue
    """
    global _setup_step

    if isinstance(msg, DriverSetupRequest):
        _setup_step = SetupSteps.INIT
        return await handle_driver_setup(msg)
    if isinstance(msg, UserDataResponse):
        _LOG.debug(msg)
        if _setup_step == SetupSteps.DEVICE_CHOICE and "choice" in msg.input_values:
            return await handle_user_data_response(msg)
        _LOG.error("No or invalid user response was received: %s", msg)
    elif isinstance(msg, AbortDriverSetup):
        _LOG.info("Setup was aborted with code: %s", msg.error)
        _setup_step = SetupSteps.INIT

    # user confirmation not used in setup process
    # if isinstance(msg, UserConfirmationResponse):
    #     return handle_user_confirmation(msg)

    return SetupError()


async def handle_driver_setup(_msg: DriverSetupRequest) -> RequestUserInput | SetupError:
    """
    Start driver setup.

    Initiated by Remote Two to set up the driver.
    Start AVR discovery and present the found devices to the user to choose from.

    :param _msg: not used, we don't have any input fields in the first setup screen.
    :return: the setup action on how to continue
    """
    global _setup_step

    _LOG.debug("Starting driver setup")
    config.devices.clear()  # triggers device instance removal

    _LOG.debug("Starting discovery")
    avrs = await avr.discover_denon_avrs()
    dropdown_items = []

    for a in avrs:
        avr_data = {"id": a["host"], "label": {"en": f"{a['friendlyName']} ({a['modelName']}) [{a['host']}]"}}
        dropdown_items.append(avr_data)

    if not dropdown_items:
        _LOG.warning("No AVRs found")
        return SetupError(error_type=IntegrationSetupError.NOT_FOUND)

    _setup_step = SetupSteps.DEVICE_CHOICE
    return RequestUserInput(
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


async def handle_user_data_response(msg: UserDataResponse) -> SetupComplete | SetupError:
    """
    Process user data response in a setup process.

    Driver setup callback to provide requested user data during the setup process.

    :param msg: response data from the requested user data
    :return: the setup action on how to continue: SetupComplete if a valid AVR device was chosen.
    """
    choice = msg.input_values["choice"]
    _LOG.debug("Chosen Denon AVR: %s", choice)

    avr_device = avr.DenonAVR(choice)
    # FIXME handle connect error!
    # TODO add timeout or a dedicated method to fetch device information and disconnect (as Android TV)
    await avr_device.connect()
    # _configured_avrs[avr_device.id] = avr_device
    #
    # _add_available_entity(avr_device.id, avr_device.name)

    # _config.append({"id": avr_device.id, "name": avr_device.name, "ipaddress": avr_device.ipaddress})
    # await store_config()

    avr_device.disconnect()

    device = AvrDevice(avr_device.id, avr_device.name, avr_device.ipaddress)
    config.devices.add(device)  # triggers DenonAVR instance creation
    config.devices.store()

    # AVR device connection will be triggered with subscribe_entities request

    await asyncio.sleep(1)

    _LOG.info("Setup successfully completed for %s", device.name)
    return SetupComplete()
