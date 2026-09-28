"""The charts cap themselves at CHART_TOP_N activities; the reports don't."""

from __future__ import annotations

import pandas as pd

import analyzer


def _comparison(n: int) -> pd.DataFrame:
    return pd.DataFrame({
        "activity_id": [f"A{i:03d}" for i in range(n)],
        "current_float": [(i * 7) % n for i in range(n)],
        "current_start": pd.date_range("2026-01-01", periods=n, freq="D"),
    })


def test_small_schedules_are_charted_in_full():
    comparison = _comparison(analyzer.CHART_TOP_N)
    assert analyzer._gantt_rows(comparison).equals(comparison)


def test_large_schedules_chart_the_least_float_in_schedule_order():
    comparison = _comparison(100)
    shown = analyzer._gantt_rows(comparison)
    assert len(shown) == analyzer.CHART_TOP_N
    assert set(shown["current_float"]) == set(range(analyzer.CHART_TOP_N))
    assert list(shown.index) == sorted(shown.index)
