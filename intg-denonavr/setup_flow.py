"""
Setup flow for Denon/Marantz AVR integration.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
from enum import IntEnum

import avr
import config
import discover
from config import AvrDevice
from denonavr.exceptions import AvrNetworkError, AvrTimoutError
from i18n import __, _a, _am
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
    CONFIGURATION_MODE = 1
    DISCOVER = 2
    DEVICE_CHOICE = 3
    RECONFIGURE = 4


_setup_step = SetupSteps.INIT
_cfg_add_device: bool = False
_reconfigured_device: AvrDevice | None = None


def setup_data_schema():
    """
    Get the JSON setup data structure for the driver.json file.

    :return: ``setup_data_schema`` json object
    """
    return {
        "title": _a("Integration setup"),
        "settings": [
            {
                "id": "info",
                "label": _a("Setup process"),
                "field": {
                    "label": {
                        "value": _am(
                            __("The integration discovers Denon and Marantz Receivers on the network."),
                            "\n\n",
                            # Translators: Make sure to include the support article link as Markdown. See English text
                            __("Please see our support article for requirements, features and restrictions."),
                        )
                    }
                },
            }
        ],
    }


def __user_input_discovery():
    # pylint: disable=line-too-long
    return RequestUserInput(
        _a("Setup mode"),
        [
            {
                "id": "info",
                "label": {"en": ""},
                "field": {
                    "label": {
                        "value": _am(
                            __("Leave blank to use auto-discovery and click _Next_."),
                            "\n\n",
                            __("The device must be on the same network as the remote."),
                        )
                    }
                },
            },
            {
                "id": "address",
                "label": _a("Manual IP address or hostname"),
                "field": {"text": {"value": ""}},
            },
        ],
    )


def __telnet_info():
    return {
        "id": "info",
        "label": _a("Please note:"),
        "field": {
            "label": {
                "value": _a(
                    "Using telnet provides realtime updates for many values but "
                    "certain receivers allow a single connection only!"
                )
            }
        },
    }


async def driver_setup_handler(msg: SetupDriver) -> SetupAction:
    """
    Dispatch driver setup requests to corresponding handlers.

    Either start the setup process or handle the selected AVR device.

    :param msg: the setup driver request object, either DriverSetupRequest or UserDataResponse
    :return: the setup action on how to continue
    """
    global _setup_step
    global _cfg_add_device
    global _reconfigured_device

    if isinstance(msg, DriverSetupRequest):
        _setup_step = SetupSteps.INIT
        _reconfigured_device = None
        _cfg_add_device = False
        return await handle_driver_setup(msg)

    if isinstance(msg, UserDataResponse):
        _LOG.debug("UserDataResponse: %s %s", msg, _setup_step)
        if _setup_step == SetupSteps.CONFIGURATION_MODE and "action" in msg.input_values:
            return await handle_configuration_mode(msg)
        if _setup_step == SetupSteps.DISCOVER and "address" in msg.input_values:
            return await _handle_discovery(msg)
        if _setup_step == SetupSteps.DEVICE_CHOICE and "choice" in msg.input_values:
            return await handle_device_choice(msg)
        if _setup_step == SetupSteps.RECONFIGURE:
            return await _handle_device_reconfigure(msg)
        _LOG.error("No or invalid user response was received: %s", msg)
    elif isinstance(msg, AbortDriverSetup):
        _LOG.info("Setup was aborted with code: %s", msg.error)
        _setup_step = SetupSteps.INIT

    return SetupError()


async def handle_driver_setup(msg: DriverSetupRequest) -> RequestUserInput | SetupError:
    """
    Start driver setup.

    Initiated by Remote Two/3 to set up the driver. The reconfigure flag determines the setup flow:

    - Reconfigure is True: show the configured devices and ask user what action to perform (add, delete, reset).
    - Reconfigure is False: clear the existing configuration and show device discovery screen.
    Ask user to enter ip-address for manual configuration, otherwise auto-discovery is used.

    :param msg: driver setup request data, only `reconfigure` flag is of interest.
    :return: the setup action on how to continue
    """
    global _setup_step

    reconfigure = msg.reconfigure
    _LOG.debug("Starting driver setup, reconfigure=%s", reconfigure)

    # workaround for web-configurator not picking up first response
    await asyncio.sleep(1)

    if reconfigure:
        _setup_step = SetupSteps.CONFIGURATION_MODE

        # get all configured devices for the user to choose from
        dropdown_devices = []
        for device in config.devices.all():
            dropdown_devices.append(
                {
                    "id": device.id,
                    "label": {"en": f"{device.name} ({device.id} - {device.address})"},
                }
            )

        # build user actions, based on available devices
        selected_action_index = 0
        dropdown_actions = [
            {
                "id": "add",
                "label": _a("Add a new device"),
            },
        ]

        # add remove & reset actions if there's at least one configured device
        if dropdown_devices:
            # pre-select configure action if at least one device exists
            selected_action_index = 1
            dropdown_actions.append(
                {
                    "id": "configure",
                    "label": _a("Configure selected device"),
                },
            )

            dropdown_actions.append(
                {
                    "id": "remove",
                    "label": _a("Delete selected device"),
                },
            )

            dropdown_actions.append(
                {
                    "id": "reset",
                    "label": _a("Reset configuration and reconfigure"),
                },
            )
        else:
            # dummy entry if no devices are available
            dropdown_devices.append({"id": "", "label": {"en": "---"}})

        return RequestUserInput(
            _a("Configuration mode"),
            [
                {
                    "field": {
                        "dropdown": {
                            "value": dropdown_devices[0]["id"],
                            "items": dropdown_devices,
                        }
                    },
                    "id": "choice",
                    "label": _a("Configured devices"),
                },
                {
                    "field": {
                        "dropdown": {
                            "value": dropdown_actions[selected_action_index]["id"],
                            "items": dropdown_actions,
                        }
                    },
                    "id": "action",
                    "label": _a("Action"),
                },
            ],
        )

    # Initial setup, make sure we have a clean configuration
    config.devices.clear()  # triggers device instance removal
    _setup_step = SetupSteps.DISCOVER
    return __user_input_discovery()


async def handle_configuration_mode(
    msg: UserDataResponse,
) -> RequestUserInput | SetupComplete | SetupError:
    """
    Process user data response in a setup process.

    If ``address`` field is set by the user: try connecting to device and retrieve model information.
    Otherwise, start AVR discovery and present the found devices to the user to choose from.

    :param msg: response data from the requested user data
    :return: the setup action on how to continue
    """
    global _setup_step
    global _cfg_add_device
    global _reconfigured_device

    action = msg.input_values["action"]

    # workaround for web-configurator not picking up first response
    await asyncio.sleep(1)

    match action:
        case "add":
            _cfg_add_device = True
        case "remove":
            choice = msg.input_values["choice"]
            if not config.devices.remove(choice):
                _LOG.warning("Could not remove device from configuration: %s", choice)
                return SetupError(error_type=IntegrationSetupError.OTHER)
            config.devices.store()
            return SetupComplete()
        case "configure":
            # Reconfigure device if the identifier has changed
            choice = msg.input_values["choice"]
            selected_device = config.devices.get(choice)
            if not selected_device:
                _LOG.warning("Can not configure device from configuration: %s", choice)
                return SetupError(error_type=IntegrationSetupError.OTHER)

            _setup_step = SetupSteps.RECONFIGURE
            _reconfigured_device = selected_device

            show_all_inputs = selected_device.show_all_inputs if selected_device.show_all_inputs else False
            use_telnet = selected_device.use_telnet if selected_device.use_telnet else False
            if use_telnet:
                connection_mode = "use_telnet"
            else:
                connection_mode = "use_http"
            volume_step = selected_device.volume_step if selected_device.volume_step else 0.5
            timeout = selected_device.timeout if selected_device.timeout else 2000
            is_denon = selected_device.is_denon

            return RequestUserInput(
                _a("Configure your AVR"),
                [
                    __show_all_inputs_cfg(show_all_inputs),
                    __manufacturer_cfg(is_denon),
                    __connection_mode_cfg(connection_mode),
                    __volume_cfg(volume_step),
                    __timeout_cfg(timeout),
                    __telnet_info(),
                ],
            )
        case "reset":
            config.devices.clear()  # triggers device instance removal
        case _:
            _LOG.error("Invalid configuration action: %s", action)
            return SetupError(error_type=IntegrationSetupError.OTHER)

    _setup_step = SetupSteps.DISCOVER
    return __user_input_discovery()


async def _handle_discovery(msg: UserDataResponse) -> RequestUserInput | SetupError:
    """
    Process user data response in a setup process.

    If ``address`` field is set by the user: try connecting to device and retrieve model information.
    Otherwise, start AVR discovery and present the found devices to the user to choose from.

    :param msg: response data from the requested user data
    :return: the setup action on how to continue
    """
    global _setup_step

    dropdown_items = []
    address = msg.input_values["address"]
    connect_denonavr: ConnectDenonAVR | None = None

    if address:
        _LOG.debug("Starting manual driver setup for %s", address)
        # simple connection check
        connect_denonavr = ConnectDenonAVR(
            address,
            avr.SETUP_TIMEOUT,
            show_all_inputs=False,
            zone2=False,
            zone3=False,
            use_telnet=False,
            update_audyssey=False,
        )

        try:
            await connect_denonavr.async_connect_receiver()
            receiver = connect_denonavr.receiver
            existing = config.devices.get(receiver.serial_number)
            if _cfg_add_device and existing:
                _LOG.warning("Manually specified device is already configured %s: %s", address, receiver.name)
                # no better error code at the moment
                return SetupError(error_type=IntegrationSetupError.OTHER)

            dropdown_items.append(
                {"id": address, "label": {"en": f"{receiver.name} ({receiver.model_name} - {address})"}}
            )
        except AvrNetworkError as ex:
            _LOG.error("Cannot connect to manually entered address %s: %s", address, ex)
            return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
        except AvrTimoutError:
            _LOG.error("Timeout connecting to manually entered address %s", address)
            return SetupError(error_type=IntegrationSetupError.TIMEOUT)
    else:
        _LOG.debug("Starting auto-discovery driver setup")
        avrs = await discover.denon_avrs()

        for a in avrs:
            avr_data = {"id": a["host"], "label": {"en": f"{a['friendlyName']} ({a['modelName']} - {a['host']})"}}

            # not sure if the serial number is always available in the discovery data
            serial_number = a["serialNumber"]
            if serial_number:
                existing = config.devices.get(serial_number)
                if _cfg_add_device and existing:
                    _LOG.info(
                        "Skipping found device '%s' %s: already configured",
                        a["friendlyName"],
                        a["host"],
                    )
                    continue
            dropdown_items.append(avr_data)

    if not dropdown_items:
        _LOG.warning("No AVRs found")
        return SetupError(error_type=IntegrationSetupError.NOT_FOUND)

    _setup_step = SetupSteps.DEVICE_CHOICE
    if connect_denonavr is None:
        _is_denon = True
    else:
        _is_denon = __is_denon_device(connect_denonavr.receiver.manufacturer)
    return RequestUserInput(
        _a("Please choose your Denon or Marantz AVR"),
        [
            {
                "field": {"dropdown": {"value": dropdown_items[0]["id"], "items": dropdown_items}},
                "id": "choice",
                "label": _a("Choose your Denon or Marantz AVR"),
            },
            __show_all_inputs_cfg(False),
            __manufacturer_cfg(_is_denon),
            # TODO #21 support multiple zones
            # {
            #     "id": "zone2",
            #     "label": {
            #         "en": "Set up Zone 2",
            #         "de": "Zone 2 einrichten",
            #         "fr": "Configurer Zone 2",
            #     },
            #     "field": {"checkbox": {"value": False}},
            # },
            # {
            #     "id": "zone3",
            #     "label": {
            #         "en": "Set up Zone 3",
            #         "de": "Zone 3 einrichten",
            #         "fr": "Configurer Zone 3",
            #     },
            #     "field": {"checkbox": {"value": False}},
            # },
            __connection_mode_cfg("use_telnet"),
            __volume_cfg(1),
            __timeout_cfg(2000),
            __telnet_info(),
        ],
    )


async def handle_device_choice(msg: UserDataResponse) -> SetupComplete | SetupError:
    """
    Process user data response in a setup process.

    Driver setup callback to provide requested user data during the setup process.

    :param msg: response data from the requested user data
    :return: the setup action on how to continue: SetupComplete if a valid AVR device was chosen.
    """
    host = msg.input_values["choice"]
    _LOG.debug("Chosen Denon/Marantz AVR: %s. Trying to connect and retrieve device information...", host)

    show_all_inputs = msg.input_values.get("show_all_inputs") == "true"
    update_audyssey = False  # not yet supported
    zone2 = msg.input_values.get("zone2") == "true"
    zone3 = msg.input_values.get("zone3") == "true"
    connection_mode = msg.input_values.get("connection_mode")
    use_telnet = connection_mode == "use_telnet"
    try:
        volume_step = float(msg.input_values.get("volume_step", 0.5))
        if volume_step < 0.1 or volume_step > 10:
            return SetupError(error_type=IntegrationSetupError.OTHER)
    except ValueError:
        return SetupError(error_type=IntegrationSetupError.OTHER)

    timeout = int(msg.input_values.get("timeout", 2000))

    # Telnet connection isn't required for connection check and retrieving model information
    connect_denonavr = ConnectDenonAVR(
        host,
        avr.SETUP_TIMEOUT,
        show_all_inputs,
        zone2,
        zone3,
        use_telnet=False,  # always False, connection only used to retrieve model information
        update_audyssey=False,  # always False, connection only used to retrieve model information
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
        return SetupError(error_type=IntegrationSetupError.OTHER)

    device = AvrDevice(
        receiver.serial_number,
        receiver.name,
        host,
        receiver.support_sound_mode,
        show_all_inputs,
        use_telnet=use_telnet,
        update_audyssey=update_audyssey,
        zone2=zone2,
        zone3=zone3,
        volume_step=volume_step,
        timeout=timeout,
        is_denon=__is_denon_device(receiver.manufacturer),
    )
    config.devices.add_or_update(device)  # triggers DenonAVR instance creation

    # AVR device connection will be triggered with subscribe_entities request

    await asyncio.sleep(1)

    _LOG.info("Setup successfully completed for %s", device.name)
    return SetupComplete()


async def _handle_device_reconfigure(
    msg: UserDataResponse,
) -> SetupComplete | SetupError:
    """
    Process reconfiguration of a configured AVR device.

    :param msg: response data from the requested user data
    :return: the setup action on how to continue: SetupComplete after updating configuration
    """
    # flake8: noqa:F824
    # pylint: disable=W0602
    global _reconfigured_device

    if _reconfigured_device is None:
        return SetupError()

    _LOG.debug("User has changed configuration")

    connection_mode = msg.input_values.get("connection_mode")
    try:
        volume_step = float(msg.input_values.get("volume_step", 0.5))
        if volume_step < 0.1 or volume_step > 10:
            return SetupError(error_type=IntegrationSetupError.OTHER)
    except ValueError:
        return SetupError(error_type=IntegrationSetupError.OTHER)

    _reconfigured_device.show_all_inputs = msg.input_values.get("show_all_inputs") == "true"
    _reconfigured_device.is_denon = __is_denon_device(msg.input_values.get("manufacturer"))
    _reconfigured_device.zone2 = msg.input_values.get("zone2") == "true"
    _reconfigured_device.zone3 = msg.input_values.get("zone3") == "true"
    _reconfigured_device.use_telnet = connection_mode == "use_telnet"
    _reconfigured_device.volume_step = volume_step
    _reconfigured_device.timeout = int(msg.input_values.get("timeout", 2000))

    config.devices.update(_reconfigured_device)  # triggers receiver instance update
    await asyncio.sleep(1)
    _LOG.info("Setup successfully completed for %s", _reconfigured_device.name)

    return SetupComplete()


def __show_all_inputs_cfg(enabled: bool):
    return {
        "id": "show_all_inputs",
        "label": _a("Show all sources"),
        "field": {"checkbox": {"value": enabled}},
    }


def __manufacturer_cfg(is_denon: bool):
    return {
        "id": "manufacturer",
        "label": _a("Select manufacturer"),
        "field": {
            "dropdown": {
                "value": "denon" if is_denon else "marantz",
                "items": [
                    {
                        "id": "denon",
                        "label": {"en": "Denon"},
                    },
                    {
                        "id": "marantz",
                        "label": {"en": "Marantz"},
                    },
                ],
            }
        },
    }


def __connection_mode_cfg(mode: str):
    return {
        "id": "connection_mode",
        "label": _a("Connection mode"),
        "field": {
            "dropdown": {
                "value": mode,
                "items": [
                    {
                        "id": "use_telnet",
                        "label": _a("Use Telnet connection"),
                    },
                    {
                        "id": "use_http",
                        "label": _a("Use HTTP connection"),
                    },
                ],
            }
        },
    }


def __volume_cfg(step: float):
    return {
        "id": "volume_step",
        "label": _a("Volume step"),
        "field": {"number": {"value": step, "min": 0.5, "max": 10, "steps": 1, "decimals": 1, "unit": {"en": "dB"}}},
    }


def __timeout_cfg(timeout: int):
    """
    Create an input configuration for the timeout setting.

    :param timeout: Connection and command timeout in milliseconds.
    :return: Setup flow input field configuration.
    """
    return {
        "id": "timeout",
        "label": _a("Connection and request timeout"),
        "field": {
            "number": {"value": timeout, "min": 250, "max": 10_000, "steps": 1, "decimals": 0, "unit": {"en": "ms"}}
        },
    }


def __is_denon_device(manufacturer: str | None) -> bool:
    """
    Check if the manufacturer is Denon.

    :param manufacturer: Manufacturer name
    :return: True if the manufacturer is Denon, False otherwise
    """
    return bool(manufacturer and manufacturer.lower().startswith("denon"))
