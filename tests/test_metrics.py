"""Tests for compare_schedules() and schedule_health_score() in src/metrics.py.

Small hand-built baseline/current activity set, not the repo's sample CSVs.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.cpm import run_cpm
from src.metrics import compare_schedules, schedule_health_score


def _activities():
    """A: no predecessor, unchanged (4d baseline and current).
    B: pred A, unchanged duration (6d) -- but slips relative to the critical
       path once C balloons, so its float erodes from 2 to 0 (becomes critical).
    C: pred A, baseline 8d -> current 8d (unchanged) but stops being the sole
       critical driver once B's own float erodes to 0 too; C instead gains
       slack (float goes from 0 to 2) as B takes over as the tighter path.
    """
    return pd.DataFrame({
        "activity_id": ["A", "B", "C"],
        "predecessors": [[], ["A"], ["A"]],
        "activity_name": ["Mobilize", "Path B", "Path C"],
        "phase": ["Phase 1", "Phase 1", "Phase 1"],
        "status": ["Complete", "In Progress", "In Progress"],
        "percent_complete": [100, 50, 50],
        "baseline_duration_days": [4, 6, 8],
        "current_duration_days": [4, 10, 8],
    })


def _comparison():
    activities = _activities()
    start = pd.Timestamp("2026-01-01")
    baseline = run_cpm(activities, duration_col="baseline_duration_days", start_date=start)
    current = run_cpm(activities, duration_col="current_duration_days", start_date=start)
    return activities, baseline, current, compare_schedules(activities, baseline, current)


def test_compare_schedules_float_and_criticality():
    activities, baseline, current, comparison = _comparison()
    by_id = comparison.set_index("activity_id")

    # B's own duration grew from 6d to 10d: it becomes the new critical driver.
    assert by_id.loc["B", "baseline_float"] == 2
    assert by_id.loc["B", "current_float"] == 0
    assert by_id.loc["B", "float_erosion"] == 2  # lost float -- real erosion
    assert by_id.loc["B", "is_critical"]
    assert not by_id.loc["B", "is_near_critical"]  # excluded once already critical

    # C is unchanged in duration but gains slack now that B is the tighter path.
    assert by_id.loc["C", "baseline_float"] == 0
    assert by_id.loc["C", "current_float"] == 2
    assert by_id.loc["C", "float_erosion"] == -2  # float increased, not eroded
    assert not by_id.loc["C", "is_critical"]
    assert by_id.loc["C", "is_near_critical"]  # within NEAR_CRITICAL_DAYS (5)

    assert by_id.loc["B", "slip_days"] == 4  # B's own finish moved out by 4 days
    assert by_id.loc["C", "slip_days"] == 0  # C's own finish is unchanged

    assert baseline.project_finish == pd.Timestamp("2026-01-13")
    assert current.project_finish == pd.Timestamp("2026-01-15")


def test_schedule_health_score_composite():
    _, baseline, current, comparison = _comparison()
    score = schedule_health_score(comparison, baseline.project_finish, current.project_finish)

    assert score["slip_days"] == 2
    assert score["schedule_score"] == pytest.approx(47.0)  # 50 - 2*1.5
    assert score["erosion_score"] == pytest.approx(25.0)  # no activity >= EROSION_THRESHOLD_DAYS (10)
    assert score["concentration_score"] == pytest.approx(0.0)  # all 3 activities critical or near-critical
    assert score["total_score"] == pytest.approx(72.0)
    assert score["pct_activities_eroded"] == pytest.approx(0.0)
    assert score["pct_activities_critical_or_near"] == pytest.approx(100.0)
