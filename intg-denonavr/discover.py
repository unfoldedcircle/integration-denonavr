"""Denon AVR device discovery with SSDP."""

import logging

import denonavr

_LOG = logging.getLogger(__name__)


async def denon_avrs() -> list[dict]:
    """
    Discover Denon AVRs on the network with SSDP.

    Returns a list of dictionaries which includes all discovered Denon AVR
    devices with keys "host", "modelName", "friendlyName", "presentationURL".
    By default, SSDP broadcasts are sent once with a 2 seconds timeout.

    :return: array of device information objects.
    """
    _LOG.debug("Starting discovery")

    avrs = await denonavr.async_discover()
    if not avrs:
        _LOG.info("No AVRs discovered")
        return []

    _LOG.info("Found AVR(s): %s", avrs)

    return avrs
