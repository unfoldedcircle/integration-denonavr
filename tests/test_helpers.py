import unittest

from helpers import key_update_helper


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
