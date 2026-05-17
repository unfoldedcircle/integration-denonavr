import unittest
from unittest.mock import AsyncMock, MagicMock

import simplecommand
from command_constants import SoundModeCommands


class TestSimpleCommandMappings(unittest.TestCase):
    class DummyDevice:
        def __init__(self, is_denon, use_telnet):
            self.is_denon = is_denon
            self.use_telnet = use_telnet

    def get_command_info(self, cmd):
        return simplecommand.ALL_COMMANDS[cmd]

    def test_get_simple_commands_denon(self):
        device = self.DummyDevice(is_denon=True, use_telnet=False)
        commands = simplecommand.get_simple_commands(device)
        denon_specific_found = False
        marantz_specific_found = False
        for cmd in commands:
            protocol, dtype = self.get_command_info(cmd)
            assert dtype in {simplecommand.DeviceType.ALL, simplecommand.DeviceType.DENON}
            assert protocol in {simplecommand.DeviceProtocol.ALL}
            if dtype == simplecommand.DeviceType.DENON:
                denon_specific_found = True
            if dtype == simplecommand.DeviceType.MARANTZ:
                marantz_specific_found = True

        assert denon_specific_found, "No Denon-specific command found"
        assert not marantz_specific_found, "Marantz-specific command found for Denon device"

    def test_get_simple_commands_marantz(self):
        device = self.DummyDevice(is_denon=False, use_telnet=False)
        commands = simplecommand.get_simple_commands(device)
        marantz_specific_found = False
        denon_specific_found = False
        for cmd in commands:
            protocol, dtype = self.get_command_info(cmd)
            assert dtype in {simplecommand.DeviceType.ALL, simplecommand.DeviceType.MARANTZ}
            assert protocol in {simplecommand.DeviceProtocol.ALL}
            if dtype == simplecommand.DeviceType.MARANTZ:
                marantz_specific_found = True
            if dtype == simplecommand.DeviceType.DENON:
                denon_specific_found = True

        assert marantz_specific_found, "No Marantz-specific command found"
        assert not denon_specific_found, "Denon-specific command found for Marantz device"


class TestImaxPassFilterArgs(unittest.IsolatedAsyncioTestCase):
    def _build_command(self):
        receiver = MagicMock()
        receiver.soundmode = MagicMock()
        receiver.soundmode.async_imax_hpf = AsyncMock()
        receiver.soundmode.async_imax_lpf = AsyncMock()
        send_command = AsyncMock()
        return simplecommand.SimpleCommand(receiver, send_command), receiver

    async def test_imax_hpf_passes_int(self):
        cmd, receiver = self._build_command()
        cases = [
            (SoundModeCommands.IMAX_HPF_40HZ, 40),
            (SoundModeCommands.IMAX_HPF_60HZ, 60),
            (SoundModeCommands.IMAX_HPF_80HZ, 80),
            (SoundModeCommands.IMAX_HPF_90HZ, 90),
            (SoundModeCommands.IMAX_HPF_100HZ, 100),
            (SoundModeCommands.IMAX_HPF_110HZ, 110),
            (SoundModeCommands.IMAX_HPF_120HZ, 120),
            (SoundModeCommands.IMAX_HPF_150HZ, 150),
            (SoundModeCommands.IMAX_HPF_180HZ, 180),
            (SoundModeCommands.IMAX_HPF_200HZ, 200),
            (SoundModeCommands.IMAX_HPF_250HZ, 250),
        ]
        for command, expected in cases:
            await cmd._handle_sound_mode_command(command)
            receiver.soundmode.async_imax_hpf.assert_awaited_with(expected)
            assert isinstance(receiver.soundmode.async_imax_hpf.await_args.args[0], int)

    async def test_imax_lpf_passes_int(self):
        cmd, receiver = self._build_command()
        cases = [
            (SoundModeCommands.IMAX_LPF_80HZ, 80),
            (SoundModeCommands.IMAX_LPF_90HZ, 90),
            (SoundModeCommands.IMAX_LPF_100HZ, 100),
            (SoundModeCommands.IMAX_LPF_110HZ, 110),
            (SoundModeCommands.IMAX_LPF_120HZ, 120),
            (SoundModeCommands.IMAX_LPF_150HZ, 150),
            (SoundModeCommands.IMAX_LPF_180HZ, 180),
            (SoundModeCommands.IMAX_LPF_200HZ, 200),
            (SoundModeCommands.IMAX_LPF_250HZ, 250),
        ]
        for command, expected in cases:
            await cmd._handle_sound_mode_command(command)
            receiver.soundmode.async_imax_lpf.assert_awaited_with(expected)
            assert isinstance(receiver.soundmode.async_imax_lpf.await_args.args[0], int)
