import unittest

from portfolio import core


def _pos(ticker, shares, price, target):
    return core.Position(ticker, shares, price, target, {"roth": shares})


TARGETS = {
    "A": {"target_weight": 0.5, "account_pref": "roth"},
    "B": {"target_weight": 0.5, "account_pref": "taxable"},
}


class ContributionTests(unittest.TestCase):
    def test_new_cash_goes_to_underweight_name(self):
        pos = [_pos("A", 10, 100, 0.5), _pos("B", 0, 100, 0.5)]  # A $1000, B $0
        orders = core.plan_contribution(pos, TARGETS, 1000)
        self.assertEqual([(o["ticker"], o["dollars"]) for o in orders], [("B", 1000.0)])

    def test_splits_proportionally_when_both_underweight(self):
        pos = [_pos("A", 0, 100, 0.5), _pos("B", 0, 100, 0.5)]
        orders = core.plan_contribution(pos, TARGETS, 1000)
        self.assertAlmostEqual(sum(o["dollars"] for o in orders), 1000)
        self.assertEqual({o["dollars"] for o in orders}, {500.0})

    def test_roth_room_fills_roth_preferred_first(self):
        pos = [_pos("A", 0, 100, 0.5), _pos("B", 0, 100, 0.5)]
        orders = core.plan_contribution(pos, TARGETS, 1000, roth_room=700)
        by = {(o["ticker"], o["account"]): o["dollars"] for o in orders}
        self.assertEqual(by[("A", "roth")], 500.0)
        self.assertEqual(by[("B", "roth")], 200.0)
        self.assertEqual(by[("B", "taxable")], 300.0)

    def test_small_trades_are_redistributed(self):
        pos = [_pos("A", 9.9, 100, 0.5), _pos("B", 0, 100, 0.5)]
        orders = core.plan_contribution(pos, TARGETS, 1000, min_trade=25)
        self.assertEqual([o["ticker"] for o in orders], ["B"])
        self.assertAlmostEqual(orders[0]["dollars"], 1000)


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.u = core.load_universe()
        self.t = core.load_targets()
        self.w = {k: v["target_weight"] for k, v in self.t.items()}

    def test_targets_sum_to_one_and_respect_position_cap(self):
        self.assertAlmostEqual(sum(self.w.values()), 1.0)
        self.assertLessEqual(max(self.w.values()), 0.10 + 1e-9)

    def test_every_target_is_in_universe(self):
        self.assertTrue(set(self.w) <= set(self.u))

    def test_aggregate_pe_is_harmonic(self):
        m = core.weighted_metrics({"KO": 0.5, "CB": 0.5}, self.u)
        expected = 1 / (0.5 / self.u["KO"]["pe_f1"] + 0.5 / self.u["CB"]["pe_f1"])
        self.assertAlmostEqual(m["pe_f1"], expected)

    def test_stress_is_weighted_shock(self):
        res = core.stress({"TSM": 1.0}, self.u)
        self.assertEqual(res["taiwan_strait"], -70)

    def test_screen_covers_each_sleeve(self):
        s = core.screen(self.u)
        n = {sl: sum(1 for r in self.u.values() if r["sleeve"] == sl) for sl in s}
        self.assertEqual({k: len(v) for k, v in s.items()}, n)


if __name__ == "__main__":
    unittest.main()
