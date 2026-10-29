import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from denonavr.exceptions import AvrCommandError, AvrInvalidResponseError, AvrNetworkError, AvrTimoutError
import httpx
import ucapi

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

    async def test_command_waits_for_running_connect(self):
        device = _device()
        release = asyncio.Event()
        volume_down = AsyncMock()

        async def update():
            await release.wait()

        with (
            patch.object(device._receiver, "async_update", side_effect=update),
            patch.object(device._receiver, "async_volume_down", volume_down),
        ):
            connect = asyncio.create_task(device.connect())
            await asyncio.sleep(0)
            command = asyncio.create_task(device.volume_down())
            await asyncio.sleep(0.01)
            volume_down.assert_not_awaited()

            release.set()
            await connect
            result = await command

        self.assertEqual(result, ucapi.StatusCodes.OK)
        volume_down.assert_awaited_once()

    async def test_command_fails_when_connect_does_not_finish(self):
        device = _device()

        async def update():
            await asyncio.Event().wait()

        with (
            patch.object(avr, "CONNECT_WAIT_FOR_COMMAND", 0.01),
            patch.object(device._receiver, "async_update", side_effect=update),
        ):
            connect = asyncio.create_task(device.connect())
            await asyncio.sleep(0)
            result = await device.volume_down()
            connect.cancel()

        self.assertEqual(result, ucapi.StatusCodes.SERVICE_UNAVAILABLE)
        self.assertTrue(device.available)

    async def test_stalled_first_attempt_is_restarted(self):
        device = _device()
        calls = 0

        async def update():
            nonlocal calls
            calls += 1
            if calls == 1:
                await asyncio.Event().wait()

        failure = AsyncMock()
        with (
            patch.object(avr, "CONNECT_STALL_TIMEOUT", 0.01),
            patch.object(device._receiver, "async_update", side_effect=update),
            patch.object(device, "_handle_connection_failure", failure),
        ):
            await device.connect()

        self.assertEqual(calls, 2)
        failure.assert_not_awaited()
        self.assertTrue(device.active)

    async def test_stall_restarts_are_limited(self):
        device = _device()
        calls = 0

        async def update():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.05)

        with (
            patch.object(avr, "CONNECT_STALL_TIMEOUT", 0.01),
            patch.object(device._receiver, "async_update", side_effect=update),
        ):
            await device.connect()

        self.assertEqual(calls, avr.CONNECT_STALL_RESTARTS + 1)
        self.assertTrue(device.active)

    async def test_command_retried_after_connect_started_during_command(self):
        device = _device()
        connect: asyncio.Task[None] | None = None
        error = AvrNetworkError("down", "req")

        async def volume_down():
            nonlocal connect
            if connect is None:
                connect = asyncio.create_task(device.connect())
                await asyncio.sleep(0)
                raise error

        volume_down_mock = AsyncMock(side_effect=volume_down)
        with (
            patch.object(device._receiver, "async_update", AsyncMock()),
            patch.object(device._receiver, "async_volume_down", volume_down_mock),
        ):
            result = await device.volume_down()

        self.assertEqual(result, ucapi.StatusCodes.OK)
        self.assertEqual(volume_down_mock.await_count, 2)
        self.assertTrue(device.available)
        self.assertTrue(device.active)

    async def test_command_network_error_without_connect_marks_unavailable(self):
        device = _device()
        volume_down = AsyncMock(side_effect=AvrNetworkError("down", "req"))
        with patch.object(device._receiver, "async_volume_down", volume_down):
            result = await device.volume_down()

        self.assertEqual(result, ucapi.StatusCodes.SERVICE_UNAVAILABLE)
        volume_down.assert_awaited_once()
        self.assertFalse(device.available)
