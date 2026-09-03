"""
Schedule Health Analyzer
-------------------------
Runs the Critical Path Method over a fictional project's activity network
twice (baseline durations, current/re-estimated durations), compares the two
schedules, and produces a schedule health report: forecast slip, float
erosion by activity, critical/near-critical concentration, and a composite
0-100 health score.

Run:
    pip install -r requirements.txt
    python analyzer.py
"""

import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from src import metrics

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

PROJECT_START = "2026-01-05"

# Standardized chart color system (chart chrome, status scale, baseline/reference)
CHART_BG = "#fcfcfb"
INK = "#10182b"
GRID = "#e1e0d9"
BASELINE = "#3a4d7a"
STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"
STATUS_CRITICAL = "#d03b3b"


def _apply_chrome(fig, axes) -> None:
    """Apply the standardized chart chrome (background, ink, gridlines) to a figure."""
    fig.patch.set_facecolor(CHART_BG)
    if hasattr(axes, "flatten"):
        axes = axes.flatten().tolist()
    elif not isinstance(axes, (list, tuple)):
        axes = [axes]
    for ax in axes:
        ax.set_facecolor(CHART_BG)
        ax.title.set_color(INK)
        ax.xaxis.label.set_color(INK)
        ax.yaxis.label.set_color(INK)
        ax.tick_params(colors=INK)
        for spine in ax.spines.values():
            spine.set_color(INK)


def status_tag(row) -> str:
    if row["status"] == "Complete":
        return "actual"
    if row["status"] == "In Progress":
        return f"in progress {int(row['percent_complete'])}%"
    return "forecast"


def criticality_tag(row) -> str:
    if row["is_critical"]:
        return "CRITICAL"
    if row["is_near_critical"]:
        return "near-critical"
    return "ok"


def print_report(comparison, score, baseline_finish, current_finish) -> None:
    print("=" * 64)
    print("SCHEDULE HEALTH REPORT")
    print("=" * 64)
    print(f"Schedule Health Score: {score['total_score']} / 100")
    print(f"  - Slip component:          {score['schedule_score']} / 50")
    print(f"  - Float erosion component: {score['erosion_score']} / 25")
    print(f"  - Critical concentration:  {score['concentration_score']} / 25")
    print()
    print(f"Baseline finish:  {baseline_finish.date()}")
    print(f"Current forecast: {current_finish.date()}  ({score['slip_days']:+d} days)")
    print(f"Activities with eroded float (>= {metrics.EROSION_THRESHOLD_DAYS}d lost): "
          f"{score['pct_activities_eroded']}%")
    print(f"Activities critical or near-critical: {score['pct_activities_critical_or_near']}%")

    print()
    print("-" * 64)
    print("CRITICAL PATH (current schedule)")
    print("-" * 64)
    critical = comparison[comparison["is_critical"]].sort_values("current_start")
    for _, row in critical.iterrows():
        print(f"  {row['activity_id']:<5} {row['activity_name']:<42} "
              f"{row['current_start'].date()} -> {row['current_finish'].date()}  "
              f"[{status_tag(row)}]")

    print()
    print("-" * 64)
    print("TOP FLOAT EROSION (baseline float lost)")
    print("-" * 64)
    top_erosion = comparison.sort_values("float_erosion", ascending=False).head(6)
    for _, row in top_erosion.iterrows():
        print(f"  {row['activity_id']:<5} {row['activity_name']:<42} "
              f"erosion={row['float_erosion']:+3d}d  "
              f"current_float={row['current_float']:+3d}d  [{criticality_tag(row)}]")


def write_report_markdown(comparison, score, baseline_finish, current_finish) -> None:
    lines = [
        "# Schedule Health Report",
        "",
        f"**Schedule Health Score: {score['total_score']} / 100**",
        "",
        "| Component | Score |",
        "|---|---|",
        f"| Slip | {score['schedule_score']} / 50 |",
        f"| Float erosion | {score['erosion_score']} / 25 |",
        f"| Critical concentration | {score['concentration_score']} / 25 |",
        "",
        f"**Baseline finish:** {baseline_finish.date()}  ",
        f"**Current forecast:** {current_finish.date()} ({score['slip_days']:+d} days)  ",
        f"**Activities with eroded float (>= {metrics.EROSION_THRESHOLD_DAYS}d lost):** "
        f"{score['pct_activities_eroded']}%  ",
        f"**Activities critical or near-critical:** {score['pct_activities_critical_or_near']}%",
        "",
        "## Critical Path (current schedule)",
        "",
        "| Activity | Start | Finish | Status |",
        "|---|---|---|---|",
    ]
    critical = comparison[comparison["is_critical"]].sort_values("current_start")
    for _, row in critical.iterrows():
        lines.append(
            f"| {row['activity_name']} | {row['current_start'].date()} "
            f"| {row['current_finish'].date()} | {status_tag(row)} |"
        )

    lines += ["", "## Top Float Erosion (baseline float lost)", "",
              "| Activity | Erosion | Current Float | Status |",
              "|---|---|---|---|"]
    top_erosion = comparison.sort_values("float_erosion", ascending=False).head(6)
    for _, row in top_erosion.iterrows():
        lines.append(
            f"| {row['activity_name']} | {row['float_erosion']:+d}d "
            f"| {row['current_float']:+d}d | {criticality_tag(row)} |"
        )
    lines.append("")

    with open(os.path.join(ASSETS_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def chart_baseline_vs_current(comparison) -> None:
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = {"CRITICAL": STATUS_CRITICAL, "near-critical": STATUS_WARNING, "ok": STATUS_GOOD}
    for i, row in enumerate(comparison.itertuples()):
        b_start = mdates.date2num(row.baseline_start)
        b_width = mdates.date2num(row.baseline_finish) - b_start
        c_start = mdates.date2num(row.current_start)
        c_width = mdates.date2num(row.current_finish) - c_start
        ax.barh(i - 0.15, b_width, left=b_start, height=0.3, color=BASELINE)
        tag = criticality_tag(row._asdict())
        ax.barh(i + 0.15, c_width, left=c_start, height=0.3, color=colors[tag])

    ax.set_yticks(range(len(comparison)))
    ax.set_yticklabels(comparison["activity_name"], fontsize=8)
    ax.invert_yaxis()
    ax.xaxis_date()
    ax.set_title("Baseline vs Current Schedule, by criticality")
    handles = [plt.Rectangle((0, 0), 1, 1, color=BASELINE, label="Baseline")]
    handles += [plt.Rectangle((0, 0), 1, 1, color=c, label=k) for k, c in colors.items()]
    ax.legend(handles=handles, loc="lower right", fontsize=8)
    ax.grid(color=GRID, linewidth=0.6, axis="x")
    _apply_chrome(fig, ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "baseline_vs_current.png"), dpi=140, facecolor=CHART_BG)
    plt.close(fig)


def chart_float_erosion(comparison) -> None:
    ranked = comparison.sort_values("float_erosion", ascending=True)
    colors = [STATUS_CRITICAL if v >= metrics.EROSION_THRESHOLD_DAYS else STATUS_GOOD
              for v in ranked["float_erosion"]]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(ranked["activity_name"], ranked["float_erosion"], color=colors)
    ax.axvline(metrics.EROSION_THRESHOLD_DAYS, color=BASELINE, linestyle="--", linewidth=1,
               label=f"Erosion threshold ({metrics.EROSION_THRESHOLD_DAYS}d)")
    ax.set_xlabel("Float erosion (days lost vs baseline float)")
    ax.set_title("Float Erosion by Activity")
    ax.legend(fontsize=8)
    ax.grid(color=GRID, linewidth=0.6, axis="x")
    _apply_chrome(fig, ax)
    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "float_erosion.png"), dpi=140, facecolor=CHART_BG)
    plt.close(fig)


def main() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)

    activities = metrics.load_activities(os.path.join(DATA_DIR, "activities.csv"))
    baseline, current = metrics.run_baseline_and_current(activities, PROJECT_START)
    comparison = metrics.compare_schedules(activities, baseline, current)
    score = metrics.schedule_health_score(comparison, baseline.project_finish, current.project_finish)

    print_report(comparison, score, baseline.project_finish, current.project_finish)
    chart_baseline_vs_current(comparison)
    chart_float_erosion(comparison)
    write_report_markdown(comparison, score, baseline.project_finish, current.project_finish)

    print()
    print("-" * 64)
    print(f"Charts and report.md saved to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
