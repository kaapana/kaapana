"""Shared metric semantics: which metrics improve by going up, which aren't
real percentages, and how to compute % change between two values.

Kept dependency-free (no matplotlib/numpy) so report.py can color-code cells
without pulling in compare.py's plotting imports.
"""

from __future__ import annotations

import math

# metrics where an increase is an improvement — color is flipped so red = worse
HIGHER_IS_BETTER = {"download_mbps", "upload_mbps", "gflops_max", "gpus_ok"}
# config values and counts where % change is meaningless (0 baselines)
NOT_A_METRIC = {"series", "burn_seconds", "failed_runs", "errors", "gpus_faulty", "objects",
                "peak_active_runs", "dropped_series", "split_runs"}


def pct_change(before: float, after: float) -> float:
    if before == 0:
        return 0.0 if after == 0 else math.nan
    return 100 * (after - before) / before


def badness(metric: str, pct: float) -> float:
    """Sign-flip pct for higher-is-better metrics, so a positive result
    always means 'worse' regardless of the metric's direction."""
    return -pct if metric in HIGHER_IS_BETTER else pct
