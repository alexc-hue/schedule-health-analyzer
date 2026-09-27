"""Regression tests for bugs fixed in commit cb6b6f9 ("Fix double-counting,
crash, and score-cap bugs from code review").

That commit's message says each fix was checked with a throwaway script that
was then discarded. These tests are that script, kept, so the same bugs
can't come back unnoticed. Each one was confirmed to fail with its fix
reverted before being committed.
"""

from __future__ import annotations

import pandas as pd
import pytest

from analyzer import status_tag
from src.cpm import run_cpm
from src.metrics import compare_schedules, schedule_health_score

START = pd.Timestamp("2026-01-01")


def _activities(**overrides):
    data = {
        "activity_id": ["A", "B"],
        "predecessors": [[], ["A"]],
        "activity_name": ["First", "Second"],
        "phase": ["P1", "P1"],
        "status": ["Complete", "In Progress"],
        "percent_complete": [100, 50],
        "baseline_duration_days": [4, 6],
        "current_duration_days": [4, 6],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_duplicate_activity_id_is_counted_once():
    """A repeated activity_id in the input must not double-count that
    activity in the comparison (and so in every percentage built on it)."""
    activities = pd.concat([_activities(), _activities().iloc[[1]]], ignore_index=True)
    baseline = run_cpm(activities, "baseline_duration_days", START)
    current = run_cpm(activities, "current_duration_days", START)

    comparison = compare_schedules(activities, baseline, current)

    assert len(comparison) == 2
    assert comparison["activity_id"].is_unique


def test_fractional_durations_are_rounded_not_truncated():
    """20.9 days has to schedule as 21, not 20."""
    activities = _activities(
        activity_id=["A"], predecessors=[[]], activity_name=["Only"], phase=["P1"],
        status=["Not Started"], percent_complete=[0],
        baseline_duration_days=[20.9], current_duration_days=[20.9],
    )
    result = run_cpm(activities, "current_duration_days", START)
    assert result.project_finish == START + pd.Timedelta(days=21)


def test_slip_component_is_capped_at_its_documented_max():
    """Finishing ahead of baseline can't push the slip component past 50."""
    activities = _activities()
    baseline = run_cpm(activities, "baseline_duration_days", START)
    current = run_cpm(activities, "current_duration_days", START)
    comparison = compare_schedules(activities, baseline, current)

    score = schedule_health_score(
        comparison,
        baseline_finish=baseline.project_finish,
        current_finish=baseline.project_finish - pd.Timedelta(days=15),
    )

    assert score["schedule_score"] == pytest.approx(50.0)


def test_in_progress_with_blank_percent_complete_does_not_crash():
    row = {"status": "In Progress", "percent_complete": float("nan")}
    assert status_tag(row) == "in progress (% complete unknown)"


@pytest.mark.parametrize(
    ("status", "expected"),
    [("COMPLETE", "actual"), (" complete ", "actual")],
)
def test_status_matching_ignores_case_and_whitespace(status, expected):
    assert status_tag({"status": status, "percent_complete": 0}) == expected


def test_in_progress_status_matching_ignores_case():
    assert status_tag({"status": " IN PROGRESS ", "percent_complete": 40}) == "in progress 40%"
