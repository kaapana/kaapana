"""Heatmaps of % change between two tags, one PNG per suite the tags share."""

from __future__ import annotations

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

import store
from metrics import HIGHER_IS_BETTER, NOT_A_METRIC, pct_change


def _rows(suite_data: dict) -> dict[str, dict[str, float]]:
    """Normalize a suite result to rows of numeric metrics: multi-scenario
    suites keep one row per scenario, flat suites become a single row."""
    if all(isinstance(v, dict) for v in suite_data.values()):
        rows = suite_data
    else:
        rows = {"overall": suite_data}
    return {
        name: {m: v for m, v in metrics.items() if isinstance(v, (int, float))}
        for name, metrics in rows.items()
    }


def _row_pct_change(b_row: dict, n_row: dict, m: str) -> float:
    if m not in b_row or m not in n_row:
        return np.nan
    return pct_change(b_row[m], n_row[m])


def heatmap(base: dict, new: dict, suite: str, out_dir) -> str | None:
    b_rows, n_rows = _rows(base["suites"][suite]), _rows(new["suites"][suite])
    names = [n for n in b_rows if n in n_rows]
    if not names:
        print(f"skipping suite '{suite}': tags share no scenario rows "
              f"(base: {sorted(b_rows)}, new: {sorted(n_rows)})")
        return None
    metrics = [m for m in dict.fromkeys(
        k for n in names for k in (*b_rows[n], *n_rows[n]))
        if m not in NOT_A_METRIC]
    # % change: positive = larger in the newer version
    data = np.array([
        [_row_pct_change(b_rows[s], n_rows[s], m) for m in metrics]
        for s in names
    ])
    for s in names:  # a 0 -> nonzero jump would otherwise hide as "no data"
        for m in metrics:
            if b_rows[s].get(m) == 0 and n_rows[s].get(m):
                print(f"warning: {suite}/{s}/{m} went from 0 to "
                      f"{n_rows[s][m]} (not representable as % change)")
    # color by badness so red is always worse, whatever the metric's direction
    badness = data * np.array([-1 if m in HIGHER_IS_BETTER else 1 for m in metrics])

    cmap = LinearSegmentedColormap.from_list("div", ["#2e64c8", "#f0efec", "#c83c3c"])
    cmap.set_bad("#e6e4df")
    limit = np.nanmax(np.abs(badness)) if not np.all(np.isnan(badness)) else 1.0
    limit = max(limit, 1.0)
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)

    fig, ax = plt.subplots(figsize=(1.6 * len(metrics) + 3, 0.55 * len(names) + 2))
    im = ax.imshow(badness, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(len(metrics)), metrics)
    ax.set_yticks(range(len(names)), names)
    ax.set_title(f"{suite}: {new['tag']} vs {base['tag']} — % change (red = worse)")
    for i in range(len(names)):
        for j in range(len(metrics)):
            if np.isnan(data[i, j]):
                continue
            ax.text(j, i, f"{data[i, j]:+.0f}%", ha="center", va="center",
                    color="white" if abs(norm(badness[i, j]) - 0.5) > 0.3 else "#33322e",
                    fontsize=9)
    fig.colorbar(im, ax=ax, label="% worse")
    fig.tight_layout()
    out = str(out_dir / f"compare_{suite}.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def compare_tags(base_tag: str, new_tag: str) -> list[str]:
    base, new = store.load(base_tag), store.load(new_tag)
    shared = [s for s in base["suites"] if s in new["suites"]]
    if not shared:
        raise SystemExit(f"tags {base_tag} and {new_tag} share no suites")
    out = [heatmap(base, new, s, store.RESULTS_DIR) for s in shared]
    return [o for o in out if o is not None]
