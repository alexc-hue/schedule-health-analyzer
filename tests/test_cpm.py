"""Tests for the forward/backward-pass CPM engine in src/cpm.py.

Small hand-built activity networks, not the repo's sample CSVs.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.cpm import run_cpm


def _activities():
    """A: no predecessor (4d). B: pred A (6d, off critical path). C: pred A
    (8d, critical). Two parallel paths off A: A->B (10d total) and A->C
    (12d total), so C is critical and B carries 2 days of float."""
    return pd.DataFrame({
        "activity_id": ["A", "B", "C"],
        "predecessors": [[], ["A"], ["A"]],
        "duration_days": [4, 6, 8],
    })


def test_run_cpm_critical_path_and_float():
    result = run_cpm(_activities(), duration_col="duration_days", start_date=pd.Timestamp("2026-01-01"))

    assert result.project_finish == pd.Timestamp("2026-01-13")  # 12 days from start

    by_id = result.schedule.set_index("activity_id")
    assert by_id.loc["A", "is_critical"]
    assert by_id.loc["C", "is_critical"]
    assert not by_id.loc["B", "is_critical"]
    assert by_id.loc["A", "total_float"] == 0
    assert by_id.loc["C", "total_float"] == 0
    assert by_id.loc["B", "total_float"] == 2

    assert by_id.loc["A", "early_start"] == pd.Timestamp("2026-01-01")
    assert by_id.loc["A", "early_finish"] == pd.Timestamp("2026-01-05")
    assert by_id.loc["C", "early_finish"] == pd.Timestamp("2026-01-13")


def test_run_cpm_raises_on_empty_activities():
    empty = pd.DataFrame({"activity_id": [], "predecessors": [], "duration_days": []})
    with pytest.raises(ValueError):
        run_cpm(empty, duration_col="duration_days", start_date=pd.Timestamp("2026-01-01"))


def test_run_cpm_raises_on_cycle():
    cyclic = pd.DataFrame({
        "activity_id": ["A", "B"],
        "predecessors": [["B"], ["A"]],
        "duration_days": [1, 1],
    })
    with pytest.raises(ValueError):
        run_cpm(cyclic, duration_col="duration_days", start_date=pd.Timestamp("2026-01-01"))
