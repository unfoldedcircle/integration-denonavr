from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock

from ucapi import StatusCodes
from ucapi.remote import Commands

from denon_remote import DenonRemote


class TestDenonRemote(TestCase):
    def test_get_int_param_from_empty_dict(self):
        result = DenonRemote._get_int_param("repeat", {}, 2)
        self.assertEqual(result, 2, "Expected default value for empty dic")

    def test_get_int_param_from_invalid_value_returns_default(self):
        result = DenonRemote._get_int_param("repeat", {"repeat": []}, 2)
        self.assertEqual(result, 2, "Expected default value from invalid parameter value")

    def test_get_int_param_from_string_value(self):
        result = DenonRemote._get_int_param("repeat", {"repeat": "1"}, 2)
        self.assertEqual(result, 1, "Expected valid int param from string representation")

    def test_get_int_param_from_float_value(self):
        result = DenonRemote._get_int_param("repeat", {"repeat": 1.2}, 2)
        self.assertEqual(result, 1, "Expected valid int param from float representation")

    def test_get_int_param_from_int_value(self):
        result = DenonRemote._get_int_param("repeat", {"repeat": 1}, 2)
        self.assertEqual(result, 1, "Expected valid int param from int representation")


class TestDenonRemoteSendCmdRepeat(IsolatedAsyncioTestCase):
    def _build_remote(self, command_results):
        remote = DenonRemote.__new__(DenonRemote)
        media_player_mock = AsyncMock()
        media_player_mock.command = AsyncMock(side_effect=list(command_results))
        remote._denon_media_player = media_player_mock
        return remote, media_player_mock

    async def test_send_cmd_all_succeed(self):
        remote, mock = self._build_remote([StatusCodes.OK, StatusCodes.OK, StatusCodes.OK])
        result = await remote.command(Commands.SEND_CMD, {"command": "MV50", "repeat": 3}, websocket=None)
        self.assertEqual(StatusCodes.OK, result)
        self.assertEqual(3, mock.command.await_count)

    async def test_send_cmd_one_fails_reports_failure(self):
        remote, mock = self._build_remote([StatusCodes.OK, StatusCodes.BAD_REQUEST, StatusCodes.OK])
        result = await remote.command(Commands.SEND_CMD, {"command": "MV50", "repeat": 3}, websocket=None)
        self.assertEqual(StatusCodes.BAD_REQUEST, result)
        self.assertEqual(3, mock.command.await_count)

    async def test_send_cmd_all_fail(self):
        remote, mock = self._build_remote([StatusCodes.BAD_REQUEST, StatusCodes.BAD_REQUEST])
        result = await remote.command(Commands.SEND_CMD, {"command": "MV50", "repeat": 2}, websocket=None)
        self.assertEqual(StatusCodes.BAD_REQUEST, result)
        self.assertEqual(2, mock.command.await_count)
