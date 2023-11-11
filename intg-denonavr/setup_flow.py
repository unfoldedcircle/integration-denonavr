"""Setup flow for Denon AVR integration."""

import asyncio
import logging
from enum import IntEnum

import avr
import config
import discover
from config import AvrDevice
from denonavr.exceptions import AvrNetworkError, AvrTimoutError
from receiver import ConnectDenonAVR
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

    avrs = await discover.denon_avrs()
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
    host = msg.input_values["choice"]
    _LOG.debug("Chosen Denon AVR: %s. Trying to connect and retrieve device information...", host)

    # TODO #19 add configuration options
    use_telnet = True
    show_all_inputs = False
    zone2 = False
    zone3 = False

    # Telnet connection not required for connection check and retrieving model information
    connect_denonavr = ConnectDenonAVR(
        host,
        avr.DEFAULT_TIMEOUT,
        show_all_inputs,
        zone2,
        zone3,
        use_telnet=False,
        update_audyssey=False,
    )

    try:
        await connect_denonavr.async_connect_receiver()
    except AvrNetworkError as ex:
        _LOG.error("Cannot connect to %s: %s", host, ex)
        return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
    except AvrTimoutError:
        _LOG.error("Timeout connecting to %s", host)
        return SetupError(error_type=IntegrationSetupError.TIMEOUT)

    receiver = connect_denonavr.receiver
    assert receiver

    if receiver.serial_number is None:
        _LOG.error("Could not get serial number of host %s: required to create a unique device", host)
        return SetupError

    device = AvrDevice(
        receiver.serial_number,
        receiver.name,
        host,
        receiver.support_sound_mode,
        show_all_inputs,
        use_telnet=use_telnet,
        zone2=zone2,
        zone3=zone3,
    )
    config.devices.add(device)  # triggers DenonAVR instance creation
    config.devices.store()

    # AVR device connection will be triggered with subscribe_entities request

    await asyncio.sleep(1)

    _LOG.info("Setup successfully completed for %s", device.name)
    return SetupComplete()
