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
    DEVICE_CHOICE = 2


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
        if _setup_step == SetupSteps.CONFIGURATION_MODE and "address" in msg.input_values:
            return await handle_configuration_mode(msg)
        if _setup_step == SetupSteps.DEVICE_CHOICE and "choice" in msg.input_values:
            return await handle_device_choice(msg)
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
    Ask user to enter ip-address for manual configuration, otherwise auto-discovery is used.

    :param _msg: not used, we don't have any input fields in the first setup screen.
    :return: the setup action on how to continue
    """
    global _setup_step

    _LOG.debug("Starting driver setup")
    _setup_step = SetupSteps.CONFIGURATION_MODE
    # pylint: disable=line-too-long
    return RequestUserInput(
        {"en": "Setup mode", "de": "Setup Modus"},
        [
            {
                "id": "info",
                "label": {"en": ""},
                "field": {
                    "label": {
                        "value": {
                            "en": (
                                "Leave blank to use auto-discovery and click _Next_."
                                "The device must be on the same network as the remote."
                            ),
                            "de": (
                                "Leer lassen, um automatische Erkennung zu verwenden und auf _Weiter_ klicken."
                                "Das Gerät muss sich im gleichen Netzwerk wie die Fernbedienung befinden."
                            ),
                            "fr": (
                                "Laissez le champ vide pour utiliser la découverte automatique et cliquez sur _Suivant_."  # noqa: E501
                                "L'appareil doit être sur le même réseau que la télécommande"
                            ),
                        }
                    }
                },
            },
            {
                "field": {"text": {"value": ""}},
                "id": "address",
                "label": {"en": "IP address", "de": "IP-Adresse", "fr": "Adresse IP"},
            },
        ],
    )


async def handle_configuration_mode(msg: UserDataResponse) -> RequestUserInput | SetupError:
    """
    Process user data response in a setup process.

    If ``address`` field is set by the user: try connecting to device and retrieve model information.
    Otherwise, start AVR discovery and present the found devices to the user to choose from.

    :param msg: response data from the requested user data
    :return: the setup action on how to continue
    """
    global _setup_step

    config.devices.clear()  # triggers device instance removal

    dropdown_items = []
    address = msg.input_values["address"]

    if address:
        _LOG.debug("Starting manual driver setup for %s", address)
        # simple connection check
        connect_denonavr = ConnectDenonAVR(
            address,
            avr.DEFAULT_TIMEOUT,
            show_all_inputs=False,
            zone2=False,
            zone3=False,
            use_telnet=False,
            update_audyssey=False,
        )

        try:
            await connect_denonavr.async_connect_receiver()
            receiver = connect_denonavr.receiver
            dropdown_items.append(
                {"id": address, "label": {"en": f"{receiver.name} ({receiver.model_name}) [{address}]"}}
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
            },
            {
                "id": "show_all_inputs",
                "label": {
                    "en": "Show all sources",
                    "de": "Alle Quellen anzeigen",
                    "fr": "Afficher tous les sources",
                },
                "field": {"checkbox": {"value": False}},
            },
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
            {
                "id": "use_telnet",
                "label": {
                    "en": "Use Telnet connection",
                    "de": "Telnet-Verbindung verwenden",
                    "fr": "Utilise une connexion Telnet",
                },
                "field": {"checkbox": {"value": True}},
            },
            {
                "id": "volume_step",
                "label": {
                    "en": "Volume step",
                    "fr": "Pallier de volume",
                },
                "field": {
                    "number": {"value": 0.5, "min": 0.5, "max": 10, "steps": 1, "decimals": 1, "unit": {"en": "dB"}}
                },
            },
            {
                "id": "info",
                "label": {"en": "Please note:", "de": "Bitte beachten:", "fr": "Veuillez noter:"},
                "field": {
                    "label": {
                        "value": {
                            "en": "Using telnet provides realtime updates for many values but "
                            "certain receivers allow a single connection only! If you enable this "
                            "setting, other apps or systems may no longer work.",
                            "de": "Die Verwendung von telnet bietet Echtzeit-Updates für viele "
                            "Werte, aber bestimmte Verstärker erlauben nur eine einzige "
                            "Verbindung! Mit dieser Einstellung können andere Apps oder Systeme "
                            "nicht mehr funktionieren.",
                            "fr": "L'utilisation de telnet fournit des mises à jour en temps réel "
                            "pour de nombreuses valeurs, mais certains amplificateurs ne "
                            "permettent qu'une seule connexion! Avec ce paramètre, d'autres "
                            "applications ou systèmes ne peuvent plus fonctionner.",
                        }
                    }
                },
            },
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
    use_telnet = msg.input_values.get("use_telnet") == "true"
    volume_step = 0.5
    try:
        volume_step = float(msg.input_values.get("volume_step", 0.5))
        if volume_step < 0.1 or volume_step > 10:
            return SetupError(error_type=IntegrationSetupError.OTHER)
    except ValueError:
        return SetupError(error_type=IntegrationSetupError.OTHER)

    # Telnet connection not required for connection check and retrieving model information
    connect_denonavr = ConnectDenonAVR(
        host,
        avr.DEFAULT_TIMEOUT,
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
    )
    config.devices.add(device)  # triggers DenonAVR instance creation
    config.devices.store()

    # AVR device connection will be triggered with subscribe_entities request

    await asyncio.sleep(1)

    _LOG.info("Setup successfully completed for %s", device.name)
    return SetupComplete()
