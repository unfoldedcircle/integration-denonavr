"""
Setup flow for Denon/Marantz AVR integration.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
from enum import IntEnum

from denonavr.exceptions import AvrNetworkError, AvrTimoutError
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

import avr
import config
import discover
from config import AvrDevice
from i18n import __, _a, _am
from receiver import ConnectDenonAVR

_LOG = logging.getLogger(__name__)


class SetupSteps(IntEnum):
    """Enumeration of setup steps to keep track of user data responses."""

    INIT = 0
    CONFIGURATION_MODE = 1
    DISCOVER = 2
    DEVICE_CHOICE = 3
    RECONFIGURE = 4


_setup_step = SetupSteps.INIT
# pylint: disable=C0103
_CFG_ADD_DEVICE: bool = False
_RECONFIGURED_DEVICE: AvrDevice | None = None


def _devices() -> config.Devices:
    """Return the configured Devices instance, raising if not initialized."""
    if config.devices is None:
        msg = "Device configuration is not initialized"
        raise RuntimeError(msg)
    return config.devices


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
                            __(
                                "Please note that this integration can take 2-4s before it's ready to send commands"
                                + " after the remote starts or wakes up."
                            ),
                            "\n\n",
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
                    + "certain receivers allow a single connection only!"
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
    global _CFG_ADD_DEVICE
    global _RECONFIGURED_DEVICE

    if isinstance(msg, DriverSetupRequest):
        _setup_step = SetupSteps.INIT
        _RECONFIGURED_DEVICE = None
        _CFG_ADD_DEVICE = False
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
        dropdown_devices = [
            {
                "id": device.id,
                "label": {"en": f"{device.name} ({device.id} - {device.address})"},
            }
            for device in _devices().all()
        ]

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
    _devices().clear()  # triggers device instance removal
    _setup_step = SetupSteps.DISCOVER
    return __user_input_discovery()


# pylint: disable=too-many-return-statements
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
    global _CFG_ADD_DEVICE
    global _RECONFIGURED_DEVICE

    action = msg.input_values["action"]

    # workaround for web-configurator not picking up first response
    await asyncio.sleep(1)

    match action:
        case "add":
            _CFG_ADD_DEVICE = True
        case "remove":
            choice = msg.input_values["choice"]
            if not _devices().remove(choice):
                _LOG.warning("Could not remove device from configuration: %s", choice)
                return SetupError(error_type=IntegrationSetupError.OTHER)
            _devices().store()
            return SetupComplete()
        case "configure":
            # Reconfigure device if the identifier has changed
            choice = msg.input_values["choice"]
            selected_device = _devices().get(choice)
            if not selected_device:
                _LOG.warning("Can not configure device from configuration: %s", choice)
                return SetupError(error_type=IntegrationSetupError.OTHER)

            _setup_step = SetupSteps.RECONFIGURE
            _RECONFIGURED_DEVICE = selected_device

            show_all_inputs = selected_device.show_all_inputs or False
            use_telnet = selected_device.use_telnet or False
            connection_mode = "use_telnet" if use_telnet else "use_http"
            volume_step = selected_device.volume_step or 0.5
            timeout = selected_device.timeout or 2000
            is_denon = selected_device.is_denon
            is_dirac_supported = selected_device.is_dirac_supported

            connect_denonavr = ConnectDenonAVR(
                selected_device.address,
                avr.SETUP_TIMEOUT,
                show_all_inputs=False,
                zone2=False,
                zone3=False,
                use_telnet=False,
                update_audyssey=False,
            )

            try:
                if not await connect_denonavr.async_connect_receiver():
                    _LOG.error("Receiver metadata incomplete for %s", selected_device.address)
                    return SetupError(error_type=IntegrationSetupError.OTHER)
                receiver = connect_denonavr.receiver
                if (
                    receiver
                    and receiver.dirac.is_dirac_supported is not None
                    and is_dirac_supported != receiver.dirac.is_dirac_supported
                ):
                    is_dirac_supported = receiver.dirac.is_dirac_supported

            except AvrNetworkError:
                _LOG.exception("Cannot connect to manually entered address %s", selected_device.address)
                return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
            except AvrTimoutError:
                _LOG.exception("Timeout connecting to manually entered address %s", selected_device.address)
                return SetupError(error_type=IntegrationSetupError.TIMEOUT)

            return RequestUserInput(
                _a("Configure your AVR"),
                [
                    __show_all_inputs_cfg(enabled=show_all_inputs),
                    __manufacturer_cfg(is_denon=is_denon),
                    __connection_mode_cfg(connection_mode),
                    __volume_cfg(volume_step),
                    __timeout_cfg(timeout),
                    __is_dirac_supported_cfg(is_supported=is_dirac_supported),
                    __telnet_info(),
                ],
            )
        case "reset":
            _devices().clear()  # triggers device instance removal
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
            if not await connect_denonavr.async_connect_receiver():
                _LOG.error("Receiver metadata incomplete for %s", address)
                return SetupError(error_type=IntegrationSetupError.OTHER)
            receiver = connect_denonavr.receiver
            if receiver is None or receiver.serial_number is None:
                _LOG.error("Receiver not available for %s", address)
                return SetupError(error_type=IntegrationSetupError.OTHER)
            existing = _devices().get(receiver.serial_number)
            if _CFG_ADD_DEVICE and existing:
                _LOG.warning("Manually specified device is already configured %s: %s", address, receiver.name)
                # no better error code at the moment
                return SetupError(error_type=IntegrationSetupError.OTHER)

            dropdown_items.append(
                {"id": address, "label": {"en": f"{receiver.name} ({receiver.model_name} - {address})"}}
            )
        except AvrNetworkError:
            _LOG.exception("Cannot connect to manually entered address %s", address)
            return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
        except AvrTimoutError:
            _LOG.exception("Timeout connecting to manually entered address %s", address)
            return SetupError(error_type=IntegrationSetupError.TIMEOUT)
    else:
        _LOG.debug("Starting auto-discovery driver setup")
        avrs = await discover.denon_avrs()

        for a in avrs:
            avr_data = {"id": a["host"], "label": {"en": f"{a['friendlyName']} ({a['modelName']} - {a['host']})"}}

            # not sure if the serial number is always available in the discovery data
            serial_number = a["serialNumber"]
            if serial_number:
                existing = _devices().get(serial_number)
                if _CFG_ADD_DEVICE and existing:
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
    connected_receiver = connect_denonavr.receiver if connect_denonavr else None
    _is_denon = True if connected_receiver is None else __is_denon_device(connected_receiver.manufacturer)
    is_dirac_supported = connected_receiver.dirac.is_dirac_supported if connected_receiver else False
    return RequestUserInput(
        _a("Please choose your Denon or Marantz AVR"),
        [
            {
                "field": {"dropdown": {"value": dropdown_items[0]["id"], "items": dropdown_items}},
                "id": "choice",
                "label": _a("Choose your Denon or Marantz AVR"),
            },
            __show_all_inputs_cfg(enabled=False),
            __manufacturer_cfg(is_denon=_is_denon),
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
            __is_dirac_supported_cfg(is_supported=is_dirac_supported),
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
        show_all_inputs=show_all_inputs,
        zone2=zone2,
        zone3=zone3,
        use_telnet=False,  # always False, connection only used to retrieve model information
        update_audyssey=False,  # always False, connection only used to retrieve model information
    )

    try:
        if not await connect_denonavr.async_connect_receiver():
            _LOG.error("Receiver metadata incomplete for %s", host)
            return SetupError(error_type=IntegrationSetupError.OTHER)
    except AvrNetworkError:
        _LOG.exception("Cannot connect to %s", host)
        return SetupError(error_type=IntegrationSetupError.CONNECTION_REFUSED)
    except AvrTimoutError:
        _LOG.exception("Timeout connecting to %s", host)
        return SetupError(error_type=IntegrationSetupError.TIMEOUT)

    receiver = connect_denonavr.receiver
    if receiver is None:
        _LOG.error("Receiver instance not available for %s", host)
        return SetupError(error_type=IntegrationSetupError.OTHER)

    # Validate required properties
    if receiver.serial_number is None or receiver.name is None or receiver.support_sound_mode is None:
        _LOG.error("Required receiver metadata missing for host %s", host)
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
        is_dirac_supported=receiver.dirac.is_dirac_supported,
    )
    _devices().add_or_update(device)  # triggers DenonAVR instance creation

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
    if _RECONFIGURED_DEVICE is None:
        return SetupError()

    _LOG.debug("User has changed configuration")

    connection_mode = msg.input_values.get("connection_mode")
    try:
        volume_step = float(msg.input_values.get("volume_step", 0.5))
        if volume_step < 0.1 or volume_step > 10:
            return SetupError(error_type=IntegrationSetupError.OTHER)
    except ValueError:
        return SetupError(error_type=IntegrationSetupError.OTHER)

    _RECONFIGURED_DEVICE.show_all_inputs = msg.input_values.get("show_all_inputs") == "true"
    _RECONFIGURED_DEVICE.is_denon = __is_denon_device(msg.input_values.get("manufacturer"))
    _RECONFIGURED_DEVICE.zone2 = msg.input_values.get("zone2") == "true"
    _RECONFIGURED_DEVICE.zone3 = msg.input_values.get("zone3") == "true"
    _RECONFIGURED_DEVICE.use_telnet = connection_mode == "use_telnet"
    _RECONFIGURED_DEVICE.volume_step = volume_step
    _RECONFIGURED_DEVICE.timeout = int(msg.input_values.get("timeout", 2000))

    _devices().update(_RECONFIGURED_DEVICE)  # triggers receiver instance update
    await asyncio.sleep(1)
    _LOG.info("Setup successfully completed for %s", _RECONFIGURED_DEVICE.name)

    return SetupComplete()


def __show_all_inputs_cfg(*, enabled: bool):
    return {
        "id": "show_all_inputs",
        "label": _a("Show all sources"),
        "field": {"checkbox": {"value": enabled}},
    }


def __manufacturer_cfg(*, is_denon: bool):
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
            "number": {"value": timeout, "min": 250, "max": 10_000, "steps": 1000, "decimals": 0, "unit": {"en": "ms"}}
        },
    }


def __is_denon_device(manufacturer: str | None) -> bool:
    """
    Check if the manufacturer is Denon.

    :param manufacturer: Manufacturer name
    :return: True if the manufacturer is Denon, False otherwise
    """
    return bool(manufacturer and manufacturer.lower().startswith("denon"))


def __is_dirac_supported_cfg(*, is_supported: bool | None):
    return {
        "id": "is_dirac_supported",
        "label": _a("Device supports Dirac"),
        "field": {
            "dropdown": {
                "value": str(is_supported) if is_supported is not None else "False",
                "items": [
                    {
                        "id": "True",
                        "label": _a("Yes"),
                    },
                    {
                        "id": "False",
                        "label": _a("No"),
                    },
                ],
            }
        },
    }
