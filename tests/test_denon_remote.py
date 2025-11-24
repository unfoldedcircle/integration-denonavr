from unittest import TestCase

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
