import os
import tempfile
import unittest
from pathlib import Path

from listing_copy.cache import CopyCache
from listing_copy.providers import OfflineProvider, parse_attributes
from listing_copy.validate import validate_copy

ROW = {
    "sku": "FOA-110",
    "name": "Roleta DEN a NOC béžová 160 cm",
    "category": "Stínicí technika",
    "attributes": "materiál: polyester; barva: béžová; šířka: 160 cm",
    "price": "1290",
    "currency": "CZK",
}


class OfflineProviderTests(unittest.TestCase):
    def test_generates_valid_copy(self):
        payload = OfflineProvider().generate(ROW)
        payload["name"] = ROW["name"]
        self.assertEqual(validate_copy(payload), [])

    def test_title_respects_limit(self):
        row = dict(ROW, name="Velmi dlouhý název produktu " * 4)
        payload = OfflineProvider().generate(row)
        self.assertLessEqual(len(payload["title"]), 70)

    def test_meta_description_limit(self):
        payload = OfflineProvider().generate(ROW)
        self.assertLessEqual(len(payload["meta_description"]), 155)

    def test_description_contains_attributes(self):
        payload = OfflineProvider().generate(ROW)
        self.assertIn("polyester", payload["description"])

    def test_parse_attributes_splits_semicolons(self):
        self.assertEqual(parse_attributes("a: 1; b: 2"), ["a: 1", "b: 2"])


class ValidationTests(unittest.TestCase):
    def test_catches_banned_claim(self):
        payload = OfflineProvider().generate(ROW)
        payload["name"] = ROW["name"]
        payload["description"] = payload["description"] + " 100% záruka"
        self.assertTrue(any("zakázaný slib" in e for e in validate_copy(payload)))

    def test_catches_short_meta(self):
        payload = OfflineProvider().generate(ROW)
        payload["name"] = ROW["name"]
        payload["meta_description"] = "krátké"
        self.assertTrue(any(e.startswith("meta_description") for e in validate_copy(payload)))

    def test_catches_caps_title(self):
        payload = OfflineProvider().generate(ROW)
        payload["name"] = ROW["name"]
        payload["title"] = "ROLETA DEN A NOC BEZOVA 160 CM"
        self.assertTrue(any("velkých písmen" in e for e in validate_copy(payload)))

    def test_alt_text_must_differ_from_name(self):
        payload = OfflineProvider().generate(ROW)
        payload["name"] = ROW["name"]
        payload["alt_text"] = ROW["name"]
        self.assertTrue(any(e.startswith("alt_text") for e in validate_copy(payload)))


class CacheTests(unittest.TestCase):
    def test_put_and_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CopyCache(Path(tmp) / "c.sqlite")
            key = CopyCache.make_key(ROW, "offline")
            self.assertIsNone(cache.get(key))
            cache.put(key, {"title": "x"})
            self.assertEqual(cache.get(key), {"title": "x"})
            cache.close()

    def test_key_depends_on_provider(self):
        self.assertNotEqual(CopyCache.make_key(ROW, "offline"), CopyCache.make_key(ROW, "openai"))


if __name__ == "__main__":
    unittest.main()
