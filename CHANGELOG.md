# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers
follow [Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-09-28

Performance at larger sizes. Output is unchanged: the console report and report.md are byte-identical to the previous release on the sample data and on generated inputs, and every chart renders pixel-identical on the sample data, so no committed image changed. The only visible difference is on inputs larger than a chart's cap, where the chart now shows a subset and says so in its title.

### Added

- `benchmarks/size_test.py`, a hand-run size test: generates bigger inputs, runs the tool end to end
  and prints run time and peak memory. Not part of CI or the test suite.
- Measured size-test numbers in the README's Limitations section.
- Tests for the chart caps and for the CPM order against the previous implementation.

### Changed

- The CPM network is ordered in one pass (Kahn's algorithm) instead of rescanning every activity
  each round. Same order, same results; a test compares it against the old implementation. 20,000
  activities now take seconds instead of most of a minute.
- Both charts show at most 30 activities: the least float on the Gantt, the most float lost on the
  erosion chart. The Gantt is drawn in two calls instead of two per activity. A full run on 5,000
  generated activities went from about 11 minutes to about 4 seconds.

## [1.1.0] - 2026-09-28

Checks and tests only. The tool's output is unchanged.

### Added

- A test that runs `analyzer.py` end to end on the sample data and checks the README's Result block against what it actually prints, so the README can't drift from the code.
- A check that the committed `assets/report.md` is exactly what the script regenerates.
- Regression tests for the code-review fixes already in 1.0.0: duplicate activity IDs counted once, fractional durations rounded rather than truncated, the slip component capped at 50, blank percent-complete handled, and status matching that ignores case and spacing.
- A test that pins the chart colors and styling shared across all six toolkit repos.
- ruff linting, run locally from `ruff.toml` and as its own CI job.
- CI now tests on Python 3.11 and 3.12, matching the "Python 3.11+" badge.
- `.gitattributes` keeps line endings consistent (LF) on every OS.

### Fixed

- `src/chart_style.py` was missing `SERIES_1`, one of the colors every toolkit repo is meant to share. No change to this repo's charts.

## [1.0.0] - 2026-09-13

First tagged release, marking the state of the repo before this changelog started. Baseline vs. current schedule through a CPM forward/backward pass, float erosion, and a three-part Schedule Health Score, with charts and a markdown report. Includes the fixes from code review, a pytest suite and CI.

[1.2.0]: https://github.com/alexc-hue/schedule-health-analyzer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/alexc-hue/schedule-health-analyzer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/alexc-hue/schedule-health-analyzer/releases/tag/v1.0.0
