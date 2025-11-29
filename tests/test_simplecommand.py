import unittest

import simplecommand


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
