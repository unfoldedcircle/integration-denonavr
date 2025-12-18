import unittest

from helpers import key_update_helper, relative_volume_to_absolute, absolute_volume_to_relative


class TestKeyUpdateHelper(unittest.TestCase):
    def test_key_update_with_new_key(self):
        attributes = {}
        original_attributes = {}
        result = key_update_helper("key1", "value1", attributes, original_attributes)
        self.assertEqual({"key1": "value1"}, result)

    def test_key_update_with_existing_key_and_same_value(self):
        attributes = {"key1": "value1"}
        original_attributes = {"key1": "value1"}
        result = key_update_helper("key1", "value1", attributes, original_attributes)
        self.assertEqual({"key1": "value1"}, result)

    def test_key_update_with_existing_key_and_different_value(self):
        attributes = {"key1": "old_value"}
        original_attributes = {"key1": "old_value"}
        result = key_update_helper("key1", "new_value", attributes, original_attributes)
        self.assertEqual({"key1": "new_value"}, result)

    def test_key_update_with_value_none(self):
        attributes = {"key1": "value1"}
        original_attributes = {"key1": "value1"}
        result = key_update_helper("key2", None, attributes, original_attributes)
        self.assertEqual({"key1": "value1"}, result)

    def test_key_update_with_missing_original_key(self):
        attributes = {"key1": "value1"}
        original_attributes = {}
        result = key_update_helper("key2", "value2", attributes, original_attributes)
        self.assertEqual({"key1": "value1", "key2": "value2"}, result)


class TestRelativeVolumeToAbsolute(unittest.TestCase):
    def test_invalid_negative_values_result_in_min(self):
        self.assertEqual(0, relative_volume_to_absolute(-100.0))
        self.assertEqual(0, relative_volume_to_absolute(-81.0))
        self.assertEqual(0, relative_volume_to_absolute(-80.5))

    def test_invalid_positive_values_result_in_max(self):
        self.assertEqual(98, relative_volume_to_absolute(18.5))
        self.assertEqual(98, relative_volume_to_absolute(19.0))
        self.assertEqual(98, relative_volume_to_absolute(100))

    def test_min_and_max_values(self):
        self.assertEqual(0, relative_volume_to_absolute(-80))
        self.assertEqual(0, relative_volume_to_absolute(-80.0))
        self.assertEqual(98, relative_volume_to_absolute(18))
        self.assertEqual(98, relative_volume_to_absolute(18.0))

    def test_relative_conversion(self):
        self.assertEqual(10, relative_volume_to_absolute(-70))
        self.assertEqual(29.5, relative_volume_to_absolute(-50.5))
        self.assertEqual(70, relative_volume_to_absolute(-10))


class TestAbsoluteVolumeToRelative(unittest.TestCase):
    def test_invalid_negative_values_result_in_min(self):
        self.assertEqual(-80, absolute_volume_to_relative(-100.0))
        self.assertEqual(-80, absolute_volume_to_relative(-1.0))
        self.assertEqual(-80, absolute_volume_to_relative(-0.5))

    def test_invalid_positive_values_result_in_max(self):
        self.assertEqual(18, absolute_volume_to_relative(98.5))
        self.assertEqual(18, absolute_volume_to_relative(99.0))
        self.assertEqual(18, absolute_volume_to_relative(100))
        self.assertEqual(18, absolute_volume_to_relative(1000))

    def test_min_and_max_values(self):
        self.assertEqual(-80, absolute_volume_to_relative(0))
        self.assertEqual(-80, absolute_volume_to_relative(0.0))
        self.assertEqual(18, absolute_volume_to_relative(98))
        self.assertEqual(18, absolute_volume_to_relative(98.0))

    def test_absolute_conversion(self):
        self.assertEqual(-70, absolute_volume_to_relative(10))
        self.assertEqual(-50.5, absolute_volume_to_relative(29.5))
        self.assertEqual(-10, absolute_volume_to_relative(70))
