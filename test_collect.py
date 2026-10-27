import json
import unittest

import collect

FIX = json.load(open("test_fixture.json"))


class ExtractUuid(unittest.TestCase):
    def test_skin_returns_uuid(self):
        self.assertEqual(collect.extract_uuid(FIX["skin"]), "d84038a5-aea4-4d5d-8486-1766f813e986")

    def test_other_item_returns_none(self):
        self.assertIsNone(collect.extract_uuid(FIX["other"]))


NOW = "2026-10-27T12:00:00Z"


def sale(auction, end, price, item):
    return {"auction": auction, "end": end, "price": price, "item": item}


class AggregateDays(unittest.TestCase):
    def test_median_low_high_coins_per_day(self):
        sales = {
            "a1": ["2026-10-26T01:00:00Z", 100, "s1"],
            "a2": ["2026-10-26T02:00:00Z", 300, "s2"],
            "a3": ["2026-10-26T03:00:00Z", 200, "s3"],
            "a4": ["2026-10-25T23:00:00Z", 50, "s4"],
        }
        days = collect.aggregate_days(sales)
        self.assertEqual(days["2026-10-26"], {"sold": 3, "coins": 600, "median": 200, "low": 100, "high": 300})
        self.assertEqual(days["2026-10-25"], {"sold": 1, "coins": 50, "median": 50, "low": 50, "high": 50})


class Merge(unittest.TestCase):
    def empty(self):
        return {"updated": "", "skins": {}, "sales": {}, "days": {}, "active": None}

    def test_new_sale_adds_skin_with_sale_end_as_first_seen(self):
        s = collect.merge(self.empty(), [sale("a1", "2026-10-20T08:00:00Z", 100, "s1")], [], None, NOW)
        self.assertEqual(s["skins"]["s1"], ["2026-10-20T08:00:00Z", 1])
        self.assertEqual(s["sales"]["a1"], ["2026-10-20T08:00:00Z", 100, "s1"])
        self.assertEqual(s["updated"], NOW)

    def test_listed_skin_uses_auction_start_as_first_seen(self):
        s = collect.merge(self.empty(), [], [{"item": "s1", "start": "2026-10-26T00:00:00Z"}], None, NOW)
        self.assertEqual(s["skins"]["s1"], ["2026-10-26T00:00:00Z", 0])

    def test_existing_skin_keeps_earlier_first_seen(self):
        s = collect.merge(self.empty(), [sale("a1", "2026-10-20T08:00:00Z", 100, "s1")], [], None, NOW)
        s = collect.merge(s, [sale("a2", "2026-10-25T08:00:00Z", 120, "s1")], [{"item": "s1", "start": "2026-10-27T00:00:00Z"}], None, NOW)
        self.assertEqual(s["skins"]["s1"], ["2026-10-20T08:00:00Z", 2])

    def test_repeated_sale_not_double_counted(self):
        one = [sale("a1", "2026-10-20T08:00:00Z", 100, "s1")]
        s = collect.merge(collect.merge(self.empty(), one, [], None, NOW), one, [], None, NOW)
        self.assertEqual(s["skins"]["s1"][1], 1)
        self.assertEqual(len(s["sales"]), 1)

    def test_old_sales_pruned_but_skin_and_count_kept(self):
        s = collect.merge(self.empty(), [sale("a1", "2026-09-01T08:00:00Z", 100, "s1")], [], None, NOW)
        self.assertNotIn("a1", s["sales"])
        self.assertEqual(s["skins"]["s1"], ["2026-09-01T08:00:00Z", 1])
        self.assertEqual(s["days"], {})

    def test_days_recomputed_from_window_only_and_old_days_frozen(self):
        s = self.empty()
        s["days"] = {"2026-08-01": {"sold": 9, "coins": 9, "median": 1, "low": 1, "high": 1}}
        s = collect.merge(s, [sale("a1", "2026-10-26T08:00:00Z", 100, "s1")], [], None, NOW)
        self.assertEqual(s["days"]["2026-08-01"]["sold"], 9)
        self.assertEqual(s["days"]["2026-10-26"]["sold"], 1)

    def test_active_replaced_when_given_kept_when_none(self):
        act = {"at": NOW, "count": 5, "lowest_bin": 123}
        s = collect.merge(self.empty(), [], [], act, NOW)
        self.assertEqual(s["active"], act)
        s = collect.merge(s, [], [], None, NOW)
        self.assertEqual(s["active"], act)

    def test_refuses_to_shrink(self):
        old = collect.merge(self.empty(), [sale("a1", "2026-10-20T08:00:00Z", 100, "s1")], [], None, NOW)
        collect.check_no_shrink(old, old)
        with self.assertRaises(AssertionError):
            collect.check_no_shrink(old, self.empty())


if __name__ == "__main__":
    unittest.main()
