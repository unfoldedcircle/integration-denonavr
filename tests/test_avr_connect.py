import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from denonavr.exceptions import AvrCommandError, AvrInvalidResponseError, AvrNetworkError, AvrTimoutError
import httpx

import avr
from config import AvrDevice


def _device() -> avr.DenonDevice:
    config = AvrDevice(
        id="id",
        name="name",
        address="127.0.0.1",
        support_sound_mode=True,
        show_all_inputs=False,
        use_telnet=False,
        update_audyssey=False,
        zone2=False,
        zone3=False,
        volume_step=0.5,
        timeout=2000,
        is_denon=True,
        is_dirac_supported=None,
    )
    return avr.DenonDevice(config)


class TestConnect(IsolatedAsyncioTestCase):
    async def test_network_errors_are_retried_fast(self):
        device = _device()
        update = AsyncMock(side_effect=[AvrNetworkError("down", "req"), AvrTimoutError("timeout", "req"), None])
        failure = AsyncMock()
        with (
            patch.object(device._receiver, "async_update", update),
            patch.object(device, "_handle_connection_failure", failure),
        ):
            await device.connect()

        self.assertEqual(update.await_count, 3)
        failure.assert_not_awaited()
        self.assertTrue(device.active)

    async def test_network_errors_use_backoff_after_retry_window(self):
        device = _device()
        update = AsyncMock(side_effect=[AvrNetworkError("down", "req"), None])
        failure = AsyncMock()
        with (
            patch.object(avr, "NETWORK_RETRY_WINDOW", 0),
            patch.object(device._receiver, "async_update", update),
            patch.object(device, "_handle_connection_failure", failure),
        ):
            await device.connect()

        failure.assert_awaited_once()
        self.assertTrue(device.active)

    async def test_other_errors_use_backoff(self):
        device = _device()
        update = AsyncMock(side_effect=[AvrCommandError("error", "req"), None])
        failure = AsyncMock()
        with (
            patch.object(device._receiver, "async_update", update),
            patch.object(device, "_handle_connection_failure", failure),
        ):
            await device.connect()

        failure.assert_awaited_once()
        self.assertTrue(device.active)

    async def test_closed_connection_is_retried_fast(self):
        device = _device()
        closed = AvrInvalidResponseError("closed", "req")
        closed.__cause__ = httpx.RemoteProtocolError("Server disconnected without sending a response.")
        update = AsyncMock(side_effect=[closed, None])
        failure = AsyncMock()
        with (
            patch.object(device._receiver, "async_update", update),
            patch.object(device, "_handle_connection_failure", failure),
        ):
            await device.connect()

        failure.assert_not_awaited()
        self.assertTrue(device.active)

    async def test_unexpected_errors_use_backoff(self):
        device = _device()
        update = AsyncMock(side_effect=[KeyError("missing"), None])
        failure = AsyncMock()
        with (
            patch.object(device._receiver, "async_update", update),
            patch.object(device, "_handle_connection_failure", failure),
            self.assertLogs("avr", "ERROR"),
        ):
            await device.connect()

        failure.assert_awaited_once()
        self.assertTrue(device.active)

    async def test_disconnect_cancels_running_connect(self):
        device = _device()
        started = asyncio.Event()

        async def update():
            started.set()
            await asyncio.Event().wait()

        with patch.object(device._receiver, "async_update", side_effect=update):
            task = asyncio.create_task(device.connect())
            await started.wait()
            await device.disconnect()

        self.assertTrue(task.cancelled())
        self.assertFalse(device.active)
        self.assertIsNone(device._connect_task)
