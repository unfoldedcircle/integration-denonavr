from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, PropertyMock, patch

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
    async def test_connect_updates_expected_volume(self):
        device = _device()
        device._expected_volume = 10.0

        with (
            patch.object(device._receiver, "async_update", AsyncMock()),
            patch.object(type(device), "volume_level", new_callable=PropertyMock, return_value=40.0),
        ):
            await device.connect()

        self.assertEqual(device._expected_volume, 40.0)
