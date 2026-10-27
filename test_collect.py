import json
import unittest

import collect

FIX = json.load(open("test_fixture.json"))


class ExtractUuid(unittest.TestCase):
    def test_skin_returns_uuid(self):
        self.assertEqual(collect.extract_uuid(FIX["skin"]), "d84038a5-aea4-4d5d-8486-1766f813e986")

    def test_other_item_returns_none(self):
        self.assertIsNone(collect.extract_uuid(FIX["other"]))


if __name__ == "__main__":
    unittest.main()
