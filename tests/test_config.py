import unittest

from config import avr_from_entity_id, create_entity_id
from ucapi import EntityTypes


class TestConfig(unittest.TestCase):
    def test_avr_from_entity_id_with_valid_media_player_entity(self):
        entity_id = "media_player.denon_avr_1"
        result = avr_from_entity_id(entity_id)
        self.assertEqual("denon_avr_1", result, "Expected AVR suffix from a valid entity ID")

    def test_avr_from_entity_id_with_valid_sensor_entity(self):
        entity_id = "sensor.volume_db.denon_avr_1"
        result = avr_from_entity_id(entity_id)
        self.assertEqual("denon_avr_1", result, "Expected AVR suffix from a valid entity ID")

    def test_avr_from_entity_id_with_invalid_sensor_entity_missing_sensor_type(self):
        entity_id = "sensor.denon_avr_1"
        result = avr_from_entity_id(entity_id)
        self.assertEqual("denon_avr_1", result, "Expected AVR suffix from an invalid sensor entity ID")

    def test_avr_from_entity_id_with_valid_select_entity(self):
        entity_id = "select.volume_db.denon_avr_1"
        result = avr_from_entity_id(entity_id)
        self.assertEqual("denon_avr_1", result, "Expected AVR suffix from a valid entity ID")

    def test_avr_from_entity_id_with_invalid_select_entity_missing_select_type(self):
        entity_id = "select.denon_avr_1"
        result = avr_from_entity_id(entity_id)
        self.assertEqual("denon_avr_1", result, "Expected AVR suffix from an invalid select entity ID")

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

    def test_create_entity_id_with_subtype(self):
        avr_id = "denon_avr_1"
        for entity_type in EntityTypes:
            sub_type = "zone2"
            result = create_entity_id(avr_id, entity_type, sub_type)
            expected = f"{entity_type.value}.{sub_type}.{avr_id}"
            self.assertEqual(expected, result, f"Expected entity ID with subtype for {entity_type.value}")

    def test_create_entity_id_without_subtype(self):
        avr_id = "denon_avr_1"
        for entity_type in EntityTypes:
            result = create_entity_id(avr_id, entity_type)
            expected = f"{entity_type.value}.{avr_id}"
            self.assertEqual(expected, result, f"Expected entity ID without subtype for {entity_type.value}")

    def test_create_entity_id_with_media_player_entity(self):
        avr_id = "denon_avr_1"
        entity_type = EntityTypes.MEDIA_PLAYER
        result = create_entity_id(avr_id, entity_type)
        expected = "media_player.denon_avr_1"
        self.assertEqual(expected, result, "Expected correct entity ID for media player")

    def test_create_entity_id_with_remote_entity(self):
        avr_id = "denon_avr_1"
        entity_type = EntityTypes.REMOTE
        result = create_entity_id(avr_id, entity_type)
        expected = "remote.denon_avr_1"
        self.assertEqual(expected, result, "Expected correct entity ID for remote")
