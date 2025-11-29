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
        for cmd in commands:
            protocol, dtype = self.get_command_info(cmd)
            assert dtype in {simplecommand.DeviceType.ALL, simplecommand.DeviceType.DENON}
            assert protocol in {simplecommand.DeviceProtocol.ALL}

    def test_get_simple_commands_marantz(self):
        device = self.DummyDevice(is_denon=False, use_telnet=False)
        commands = simplecommand.get_simple_commands(device)
        for cmd in commands:
            protocol, dtype = self.get_command_info(cmd)
            assert dtype in {simplecommand.DeviceType.ALL, simplecommand.DeviceType.MARANTZ}
            assert protocol in {simplecommand.DeviceProtocol.ALL}
