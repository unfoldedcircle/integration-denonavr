"""
Setup flow for Denon AVR integration.

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

# pylint: disable=line-too-long
_user_input_discovery = RequestUserInput(
    {"en": "Setup mode", "de": "Setup Modus", "fr": "Installation"},
    [
        {
            "id": "info",
            "label": {"en": ""},
            "field": {
                "label": {
                    "value": {
                        "en": (
                            "Leave blank to use auto-discovery and click _Next_.\n\n"
                            "The device must be on the same network as the remote."
                        ),
                        "de": (
                            "Leer lassen, um automatische Erkennung zu verwenden und auf _Weiter_ klicken.\n\n"
                            "Das Gerät muss sich im gleichen Netzwerk wie die Fernbedienung befinden."
                        ),
                        "fr": (
                            "Laissez le champ vide pour utiliser la découverte automatique et cliquez sur _Suivant_.\n\n"  # noqa: E501
                            "L'appareil doit être sur le même réseau que la télécommande"
                        ),
                    }
                }
            },
        },
        {
            "id": "address",
            "label": {
                "en": "Manual IP address or hostname",
                "de": "Manuelle IP-Adresse oder Hostname",
                "fr": "Adresse IP manuelle ou nom d’hôte",
            },
            "field": {"text": {"value": ""}},
        },
    ],
)

_telnet_info = {
    "id": "info",
    "label": {"en": "Please note:", "de": "Bitte beachten:", "fr": "Veuillez noter:"},
    "field": {
        "label": {
            "value": {
                "en": "Using telnet provides realtime updates for many values but "
                "certain receivers allow a single connection only! If you enable this "
                "setting, other apps or systems may no longer work. "
                "Using Telnet for events is faster for regular commands while still providing realtime"
                " updates. Same limitations regarding Telnet apply.",
                "de": "Die Verwendung von telnet bietet Echtzeit-Updates für viele "
                "Werte, aber bestimmte Verstärker erlauben nur eine einzige "
                "Verbindung! Mit dieser Einstellung können andere Apps oder Systeme "
                "nicht mehr funktionieren. "
                "Die Verwendung von Telnet für Ereignisse ist schneller für normale Befehle, "
                "bietet aber immer noch Echtzeit-Updates. Die gleichen Einschränkungen in Bezug auf Telnet"
                " gelten.",
                "fr": "L'utilisation de telnet fournit des mises à jour en temps réel "
                "pour de nombreuses valeurs, mais certains amplificateurs ne "
                "permettent qu'une seule connexion! Avec ce paramètre, d'autres "
                "applications ou systèmes ne peuvent plus fonctionner. "
                "L'utilisation de Telnet pour les événements est plus rapide pour les commandes classiques "
                "tout en fournissant des mises à jour en temps réel. Les mêmes limitations concernant"
                " Telnet s'appliquent.",
            }
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

    Initiated by Remote Two to set up the driver. The reconfigure flag determines the setup flow:

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

        # TODO #27 externalize language texts
        # build user actions, based on available devices
        selected_action_index = 0
        dropdown_actions = [
            {
                "id": "add",
                "label": {
                    "en": "Add a new device",
                    "de": "Neues Gerät hinzufügen",
                    "fr": "Ajouter un nouvel appareil",
                },
            },
        ]

        # add remove & reset actions if there's at least one configured device
        if dropdown_devices:
            # pre-select configure action if at least one device exists
            selected_action_index = 1
            dropdown_actions.append(
                {
                    "id": "configure",
                    "label": {
                        "en": "Configure selected device",
                        "de": "Selektiertes Gerät konfigurieren",
                        "fr": "Configurer l'appareil sélectionné",
                    },
                },
            )

            dropdown_actions.append(
                {
                    "id": "remove",
                    "label": {
                        "en": "Delete selected device",
                        "de": "Selektiertes Gerät löschen",
                        "fr": "Supprimer l'appareil sélectionné",
                    },
                },
            )

            dropdown_actions.append(
                {
                    "id": "reset",
                    "label": {
                        "en": "Reset configuration and reconfigure",
                        "de": "Konfiguration zurücksetzen und neu konfigurieren",
                        "fr": "Réinitialiser la configuration et reconfigurer",
                    },
                },
            )
        else:
            # dummy entry if no devices are available
            dropdown_devices.append({"id": "", "label": {"en": "---"}})

        return RequestUserInput(
            {"en": "Configuration mode", "de": "Konfigurations-Modus"},
            [
                {
                    "field": {
                        "dropdown": {
                            "value": dropdown_devices[0]["id"],
                            "items": dropdown_devices,
                        }
                    },
                    "id": "choice",
                    "label": {
                        "en": "Configured devices",
                        "de": "Konfigurierte Geräte",
                        "fr": "Appareils configurés",
                    },
                },
                {
                    "field": {
                        "dropdown": {
                            "value": dropdown_actions[selected_action_index]["id"],
                            "items": dropdown_actions,
                        }
                    },
                    "id": "action",
                    "label": {
                        "en": "Action",
                        "de": "Aktion",
                        "fr": "Appareils configurés",
                    },
                },
            ],
        )

    # Initial setup, make sure we have a clean configuration
    config.devices.clear()  # triggers device instance removal
    _setup_step = SetupSteps.DISCOVER
    return _user_input_discovery


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

            return RequestUserInput(
                {
                    "en": "Configure your AVR",
                    "de": "Konfiguriere deinen Denon AVR",
                    "fr": "Configurez votre AVR",
                },
                [
                    __show_all_inputs_cfg(show_all_inputs),
                    __connection_mode_cfg(connection_mode),
                    __volume_cfg(volume_step),
                    __timeout_cfg(timeout),
                    _telnet_info,
                ],
            )
        case "reset":
            config.devices.clear()  # triggers device instance removal
        case _:
            _LOG.error("Invalid configuration action: %s", action)
            return SetupError(error_type=IntegrationSetupError.OTHER)

    _setup_step = SetupSteps.DISCOVER
    return _user_input_discovery


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
            },
            __show_all_inputs_cfg(False),
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
            _telnet_info,
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
    _LOG.debug("Chosen Denon AVR: %s. Trying to connect and retrieve device information...", host)

    show_all_inputs = msg.input_values.get("show_all_inputs") == "true"
    update_audyssey = False  # not yet supported
    zone2 = msg.input_values.get("zone2") == "true"
    zone3 = msg.input_values.get("zone3") == "true"
    connection_mode = msg.input_values.get("connection_mode")
    use_telnet = connection_mode == "use_telnet"
    volume_step = 0.5
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
        return SetupError

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
    _reconfigured_device.zone2 = msg.input_values.get("zone2") == "true"
    _reconfigured_device.zone3 = msg.input_values.get("zone3") == "true"
    _reconfigured_device.use_telnet = connection_mode == "use_telnet"
    _reconfigured_device.volume_step = volume_step
    _reconfigured_device.timeout = int(msg.input_values.get("timeout", 2000))

    config.devices.update(_reconfigured_device)  # triggers ATV instance update
    await asyncio.sleep(1)
    _LOG.info("Setup successfully completed for %s", _reconfigured_device.name)

    return SetupComplete()


def __show_all_inputs_cfg(enabled: bool):
    return {
        "id": "show_all_inputs",
        "label": {
            "en": "Show all sources",
            "de": "Alle Quellen anzeigen",
            "fr": "Afficher tous les sources",
        },
        "field": {"checkbox": {"value": enabled}},
    }


def __connection_mode_cfg(mode: str):
    return {
        "id": "connection_mode",
        "label": {
            "en": "Connection mode",
            "de": "Verbindungstyp",
            "fr": "Mode de connexion",
        },
        "field": {
            "dropdown": {
                "value": mode,
                "items": [
                    {
                        "id": "use_telnet",
                        "label": {
                            "en": "Use Telnet connection",
                            "de": "Telnet-Verbindung verwenden",
                            "fr": "Utilise une connexion Telnet",
                        },
                    },
                    {
                        "id": "use_http",
                        "label": {
                            "en": "Use HTTP connection",
                            "de": "HTTP-Verbindung verwenden",
                            "fr": "Utilise une connexion HTTP",
                        },
                    },
                ],
            }
        },
    }


def __volume_cfg(step: float):
    return {
        "id": "volume_step",
        "label": {
            "en": "Volume step",
            "fr": "Pallier de volume",
        },
        "field": {"number": {"value": step, "min": 0.5, "max": 10, "steps": 1, "decimals": 1, "unit": {"en": "dB"}}},
    }


def __timeout_cfg(timeout: int):
    return {
        "id": "timeout",
        "label": {
            "en": "Connection and request timeout",
            "de": "Verbindungs- und Anforderungszeitüberschreitung",
            "fr": "Délai de connexion et de requête",
        },
        "field": {
            "number": {"value": timeout, "min": 250, "max": 10000, "steps": 1, "decimals": 0, "unit": {"en": "ms"}}
        },
    }
