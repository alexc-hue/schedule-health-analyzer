"""The single-pass topological order has to match the original round-by-round
version exactly, since every CPM result is built in that order.

_reference_order below is the pre-1.2.0 implementation, kept here only as the
yardstick. It is compared against the current one on random networks of
different shapes, plus the error cases.
"""

from __future__ import annotations

import random

import pandas as pd
import pytest

from src.cpm import _topological_order


def _reference_order(activities: pd.DataFrame) -> list[str]:
    predecessors = {row.activity_id: set(row.predecessors) for row in activities.itertuples()}
    remaining = dict(predecessors)
    resolved: list[str] = []
    resolved_set: set[str] = set()
    while remaining:
        ready = sorted(aid for aid, preds in remaining.items() if preds <= resolved_set)
        if not ready:
            raise ValueError("Cycle detected in activity network (or an unknown predecessor id).")
        for aid in ready:
            resolved.append(aid)
            resolved_set.add(aid)
            del remaining[aid]
    return resolved


def _network(n: int, window: int, max_preds: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    ids = [f"A{i:04d}" for i in range(n)]
    rng.shuffle(ids)  # IDs out of dependency order, so the within-round sort matters
    preds = []
    for i in range(n):
        pool = ids[max(0, i - window):i]
        k = rng.randint(0, min(max_preds, len(pool)))
        preds.append(rng.sample(pool, k))
    return pd.DataFrame({"activity_id": ids, "predecessors": preds})


@pytest.mark.parametrize(
    ("n", "window", "max_preds", "seed"),
    [(1, 1, 0, 0), (50, 5, 2, 1), (300, 20, 3, 2), (300, 300, 6, 3), (2000, 40, 2, 4)],
)
def test_order_matches_reference(n, window, max_preds, seed):
    activities = _network(n, window, max_preds, seed)
    assert _topological_order(activities) == _reference_order(activities)


def test_duplicate_ids_keep_the_last_row_like_the_reference():
    activities = pd.DataFrame({
        "activity_id": ["A", "B", "B"],
        "predecessors": [[], [], ["A"]],
    })
    assert _topological_order(activities) == _reference_order(activities) == ["A", "B"]


@pytest.mark.parametrize("preds", [[["B"], ["A"]], [["A"], []], [["X"], []]])
def test_cycles_self_loops_and_unknown_ids_raise(preds):
    activities = pd.DataFrame({"activity_id": ["A", "B"], "predecessors": preds})
    with pytest.raises(ValueError, match="Cycle detected"):
        _topological_order(activities)
    with pytest.raises(ValueError, match="Cycle detected"):
        _reference_order(activities)
