"""Regression tests for bugs fixed in commit cb6b6f9 ("Fix double-counting,
crash, and score-cap bugs from code review").

That commit's message says each fix was checked with a throwaway script that
was then discarded. These tests are that script, kept, so the same bugs
can't come back unnoticed. Each one was confirmed to fail with its fix
reverted before being committed.

The section marked 1.2.2 at the end covers that release's fixes, each also
written to fail before its fix went in.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import analyzer
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


# --- 1.2.2 -------------------------------------------------------------------

def _tied_comparison(n: int = 200) -> pd.DataFrame:
    """Many rows sharing a handful of start dates and erosion values, in a known input order."""
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "activity_id": [f"A{i:03d}" for i in range(n)],
        "is_critical": True,
        "current_start": pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.integers(0, 3, n), unit="D"),
        "float_erosion": rng.integers(0, 3, n),
    })


def _ties_keep_input_order(rows: pd.DataFrame, key: str) -> bool:
    return all(list(group.index) == sorted(group.index) for _, group in rows.groupby(key))


def test_critical_path_ties_keep_input_order():
    """The default sort isn't stable, so tied start dates could swap order between runs."""
    assert _ties_keep_input_order(analyzer.critical_path_rows(_tied_comparison()), "current_start")


def test_top_erosion_ties_keep_input_order():
    comparison = _tied_comparison()
    assert _ties_keep_input_order(analyzer.top_erosion_rows(comparison, n=len(comparison)), "float_erosion")


def test_float_erosion_chart_draws_one_bar_per_activity_with_duplicate_names(monkeypatch, tmp_path):
    """Activity names used to be the bar positions, so two activities with the same
    name were drawn as one bar."""
    comparison = pd.DataFrame({
        "activity_id": ["A", "B", "C"],
        "activity_name": ["Cable pull", "Cable pull", "Terminations"],
        "float_erosion": [3, 12, 5],
    })
    real_close = plt.close
    figures = []
    monkeypatch.setattr(analyzer, "ASSETS_DIR", str(tmp_path))
    monkeypatch.setattr(plt, "close", figures.append)
    analyzer.chart_float_erosion(comparison)
    monkeypatch.undo()

    ax = figures[0].axes[0]
    bar_positions = {round(bar.get_y(), 6) for bar in ax.patches}
    tick_labels = [label.get_text() for label in ax.get_yticklabels()]
    real_close(figures[0])
    assert len(bar_positions) == 3
    assert tick_labels.count("Cable pull") == 2
