import unittest

from config import avr_from_entity_id


class TestConfig(unittest.TestCase):
    def test_avr_from_entity_id_with_valid_entity(self):
        entity_id = "media_player.denon_avr_1"
        result = avr_from_entity_id(entity_id)
        self.assertEqual("denon_avr_1", result, "Expected AVR suffix from a valid entity ID")

    def test_avr_from_entity_id_with_invalid_entity_missing_dot(self):
        entity_id = "media_player_denon_avr_1"
        result = avr_from_entity_id(entity_id)
        self.assertIsNone(result, "Expected None for an invalid entity ID with no dot")

    def test_avr_from_entity_id_with_empty_entity(self):
        entity_id = ""
        result = avr_from_entity_id(entity_id)
        self.assertIsNone(result, "Expected None for an empty entity ID")

    def test_avr_from_entity_id_with_dot_at_start(self):
        entity_id = ".denon_avr_1"
        result = avr_from_entity_id(entity_id)
        self.assertEqual("denon_avr_1", result, "Expected AVR suffix for entity ID starting with a dot")

    def test_avr_from_entity_id_with_dot_at_end(self):
        entity_id = "media_player."
        result = avr_from_entity_id(entity_id)
        self.assertEqual("", result, "Expected an empty string for an entity ID ending with a dot")
