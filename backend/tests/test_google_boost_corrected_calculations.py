"""
Tests for corrected google_added_usable / final_usable field semantics.

Key invariants:
  google_added_usable = max(0, live_after - max(finnhub_usable, live_before))
  final_usable        = finnhub_usable + google_added_usable
  rescued_to_3        = finnhub_usable < 3 AND final_usable >= 3
  boosted_to_10       = finnhub_usable < 10 AND final_usable >= 10
"""

import pytest


def _calc(finnhub_usable: int, live_before: int, live_after: int):
    google_added = max(0, live_after - max(finnhub_usable, live_before))
    final        = finnhub_usable + google_added
    rescued      = finnhub_usable < 3  and final >= 3
    boosted      = finnhub_usable < 10 and final >= 10
    return google_added, final, rescued, boosted


# ── google_added_usable ───────────────────────────────────────────────────────

class TestGoogleAddedUsable:
    def test_google_adds_above_stable_baseline(self):
        added, final, _, _ = _calc(5, 5, 8)
        assert added == 3
        assert final == 8

    def test_drift_down_google_refills_exactly_to_baseline_no_credit(self):
        # FH baseline=7, live drifted to 1, Google refills to 7: 0 net new
        added, final, _, _ = _calc(7, 1, 7)
        assert added == 0
        assert final == 7

    def test_drift_down_google_adds_above_baseline(self):
        # FH=7, drifted to 1, Google pushes to 9: only 2 above baseline credited
        added, final, _, _ = _calc(7, 1, 9)
        assert added == 2
        assert final == 9

    def test_drift_down_google_cannot_reach_baseline(self):
        # FH=7, drifted to 1, Google only reaches 4: 0 net new (below baseline)
        added, final, _, _ = _calc(7, 1, 4)
        assert added == 0
        assert final == 7  # final stays at FH baseline

    def test_no_drift_google_adds_nothing(self):
        added, final, _, _ = _calc(5, 5, 5)
        assert added == 0
        assert final == 5

    def test_fh_zero_google_adds_four(self):
        added, final, _, _ = _calc(0, 0, 4)
        assert added == 4
        assert final == 4

    def test_live_before_above_fh_baseline_google_still_counted(self):
        # Live DB already above FH baseline — shouldn't happen in practice but handle
        added, final, _, _ = _calc(5, 8, 10)
        assert added == 2   # max(0, 10 - max(5, 8)) = 2
        assert final == 7   # 5 + 2

    def test_no_negative_added(self):
        # Google never reduces the count
        added, final, _, _ = _calc(5, 5, 3)
        assert added == 0
        assert final == 5

    def test_live_after_equal_live_before_and_below_fh(self):
        added, final, _, _ = _calc(7, 2, 2)
        assert added == 0
        assert final == 7


# ── final_usable ─────────────────────────────────────────────────────────────

class TestFinalUsable:
    def test_final_is_fh_plus_google_added(self):
        added, final, _, _ = _calc(5, 5, 8)
        assert final == 5 + added

    def test_final_never_less_than_fh_usable(self):
        _, final, _, _ = _calc(7, 7, 3)   # Google reduced live DB — impossible but safe
        assert final >= 7

    def test_final_equals_fh_when_google_adds_nothing(self):
        _, final, _, _ = _calc(9, 9, 9)
        assert final == 9


# ── rescued_to_3 ──────────────────────────────────────────────────────────────

class TestRescuedTo3:
    def test_fh_below3_final_above3_is_rescued(self):
        _, _, rescued, _ = _calc(2, 2, 5)
        assert rescued is True

    def test_fh_exactly3_not_rescued(self):
        _, _, rescued, _ = _calc(3, 3, 6)
        assert rescued is False

    def test_fh_above3_not_rescued(self):
        _, _, rescued, _ = _calc(5, 5, 8)
        assert rescued is False

    def test_fh_below3_final_below3_not_rescued(self):
        _, _, rescued, _ = _calc(1, 1, 2)
        assert rescued is False

    def test_fh_below3_final_exactly3_is_rescued(self):
        _, _, rescued, _ = _calc(2, 2, 3)
        assert rescued is True

    def test_drift_case_not_rescued(self):
        # FH=5, drifted to 0, Google refills to 3 → google_added=0, final=5, NOT rescued
        _, _, rescued, _ = _calc(5, 0, 3)
        assert rescued is False

    def test_genuine_rescue_fh0_google_adds3(self):
        _, _, rescued, _ = _calc(0, 0, 3)
        assert rescued is True


# ── boosted_to_10 ────────────────────────────────────────────────────────────

class TestBoostedTo10:
    def test_fh_below10_final_above10_is_boosted(self):
        _, _, _, boosted = _calc(9, 9, 11)
        assert boosted is True

    def test_fh_exactly10_not_boosted(self):
        _, _, _, boosted = _calc(10, 10, 12)
        assert boosted is False

    def test_fh_below10_final_below10_not_boosted(self):
        _, _, _, boosted = _calc(7, 7, 9)
        assert boosted is False

    def test_fh_below10_final_exactly10_is_boosted(self):
        _, _, _, boosted = _calc(8, 8, 10)
        assert boosted is True

    def test_drift_case_not_boosted(self):
        # FH=9, drifted to 2, Google pushes to 9 (just refills) → google_added=0, final=9, NOT boosted
        _, _, _, boosted = _calc(9, 2, 9)
        assert boosted is False

    def test_drift_plus_new_is_boosted(self):
        # FH=9, drifted to 2, Google pushes to 11 → google_added=2, final=11, boosted
        _, _, _, boosted = _calc(9, 2, 11)
        assert boosted is True


# ── aggregate consistency ─────────────────────────────────────────────────────

class TestAggregateConsistency:
    """If google_added_usable is 0 for all tickers, Finnhub-only == Google-assisted."""

    def test_no_google_contributions_means_identical_ge3_counts(self):
        fh_baselines = [0, 1, 2, 3, 4, 5, 10, 15]
        results = [_calc(fh, fh, fh) for fh in fh_baselines]
        for fh, (added, final, _, _) in zip(fh_baselines, results):
            assert added == 0
            assert final == fh

    def test_full_universe_ge3_never_goes_down_when_google_adds(self):
        # If google_added >= 0 always, final >= finnhub_usable → ge3 can only stay same or go up
        tickers = [
            (0, 0, 5), (1, 1, 4), (2, 2, 3), (3, 3, 3), (5, 5, 7), (9, 9, 10)
        ]
        for fh, lb, la in tickers:
            added, final, _, _ = _calc(fh, lb, la)
            assert final >= fh, f"final {final} < fh {fh} — impossible"

    def test_all_drift_refills_produce_zero_google_added(self):
        # The "142 rescued" bug case: FH>=3 tickers that drifted below 3 in live DB
        drift_cases = [
            (7, 1, 7),   # AEP pattern
            (8, 1, 8),   # AMP pattern
            (5, 1, 5),   # AMT pattern
            (5, 1, 5),   # ARES pattern
            (6, 1, 6),   # ATO pattern
        ]
        for fh, lb, la in drift_cases:
            added, final, rescued, _ = _calc(fh, lb, la)
            assert added == 0, f"FH={fh} lb={lb} la={la}: expected added=0 got {added}"
            assert final == fh
            assert not rescued, f"FH={fh} (>=3) should never be rescued"
