from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import ucapi

import driver


class TestOnAvrConnected(IsolatedAsyncioTestCase):
    async def test_full_state_is_sent_after_connect(self):
        receiver = MagicMock()
        api = MagicMock()
        api.set_device_state = AsyncMock()
        with (
            patch.object(driver, "api", api),
            patch.object(driver, "_configured_avrs", {"id": receiver}),
            patch.object(driver, "on_avr_update") as on_avr_update,
        ):
            await driver.on_avr_connected("id")

        api.set_device_state.assert_awaited_once_with(ucapi.DeviceStates.CONNECTED)
        on_avr_update.assert_called_once_with("id", None)

    async def test_unconfigured_avr_is_ignored(self):
        api = MagicMock()
        api.set_device_state = AsyncMock()
        with (
            patch.object(driver, "api", api),
            patch.object(driver, "_configured_avrs", {}),
            patch.object(driver, "on_avr_update") as on_avr_update,
        ):
            await driver.on_avr_connected("id")

        api.set_device_state.assert_not_awaited()
        on_avr_update.assert_not_called()
