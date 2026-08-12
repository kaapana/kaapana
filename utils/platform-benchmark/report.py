"""Self-contained HTML report: every stored tag side by side, per suite and
scenario, with the compare heatmap PNGs embedded — one file to attach as a CI
artifact or send around."""

from __future__ import annotations

import base64
import html
import math
import time
from pathlib import Path

import store
from metrics import NOT_A_METRIC, badness, pct_change


def _rows(suite_data: dict) -> dict[str, dict[str, float]]:
    """Same normalization as compare._rows, duplicated here so the report
    works without matplotlib: multi-scenario suites keep one row per
    scenario, flat suites become a single 'overall' row."""
    rows = suite_data if all(
        isinstance(v, dict) for v in suite_data.values()) else {"overall": suite_data}
    return {
        name: {m: v for m, v in metrics.items() if isinstance(v, (int, float))}
        for name, metrics in rows.items()
    }

STYLE = """
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 70rem;
       color: #33322e; }
h1 { border-bottom: 2px solid #c8c5bd; padding-bottom: .3rem; }
h2 { margin-top: 2.5rem; }
table { border-collapse: collapse; margin: .8rem 0 1.5rem; }
th, td { border: 1px solid #c8c5bd; padding: .35rem .8rem; text-align: right; }
th { background: #f0efec; }
td:first-child, th:first-child { text-align: left; }
.err { color: #c83c3c; }
img { max-width: 100%; margin: 1rem 0; }
.meta { color: #7a776f; font-size: .9rem; }
"""


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:g}"
    return html.escape(str(v))


def _color(badness_pct: float, clip: float = 50.0) -> str:
    """Diverging red(worse)/blue(better) background, saturating at clip%
    — the same 'red is always worse' convention as compare.py's heatmaps."""
    t = max(-1.0, min(1.0, badness_pct / clip))
    if t >= 0:
        r, g, b = 255, round(255 * (1 - t)), round(255 * (1 - t))
    else:
        r, g, b = round(255 * (1 + t)), round(255 * (1 + t)), 255
    return f"rgb({r},{g},{b})"


def _row_cells(cols: list[str], per_tag: dict, scen: str, m: str) -> str:
    """Cells for one metric row, colored by % change vs. the closest earlier
    column that had this metric — a trend view across every stored tag
    (i.e. every MR that ran the benchmark), not just a single before/after."""
    cells, prev = [], None
    for t in cols:
        if m not in per_tag[t][scen]:
            cells.append("<td>—</td>")
            continue
        val = per_tag[t][scen][m]
        style = ""
        if prev is not None and m not in NOT_A_METRIC:
            pct = pct_change(prev, val)
            if not math.isnan(pct):
                style = f' style="background:{_color(badness(m, pct))}"'
        cells.append(f"<td{style}>{_fmt(val)}</td>")
        prev = val
    return "".join(cells)


def _suite_section(suite: str, docs: dict[str, dict]) -> str:
    """One table per scenario: metrics as rows, tags as columns."""
    tags = [t for t, d in docs.items() if suite in d["suites"]]
    per_tag = {t: _rows(docs[t]["suites"][suite]) for t in tags}
    scenarios = list(dict.fromkeys(s for t in tags for s in per_tag[t]))
    out = [f"<h2>{html.escape(suite)}</h2>"]
    for scen in scenarios:
        cols = [t for t in tags if scen in per_tag[t]]
        metrics = list(dict.fromkeys(m for t in cols for m in per_tag[t][scen]))
        out.append(f"<h3>{html.escape(scen)}</h3>")
        head = "".join(f"<th>{html.escape(t)}</th>" for t in cols)
        rows = []
        for m in metrics:
            cells = _row_cells(cols, per_tag, scen, m)
            rows.append(f"<tr><td>{html.escape(m)}</td>{cells}</tr>")
        # non-numeric entries (errors, slowest_tasks) are dropped by _rows;
        # surface scenario errors explicitly so a failed run is not invisible
        errs = [
            f"<div class='err'>{html.escape(t)}: "
            f"{html.escape(str(docs[t]['suites'][suite].get(scen, {}).get('error')))}</div>"
            for t in cols
            if isinstance(docs[t]["suites"][suite].get(scen), dict)
            and docs[t]["suites"][suite][scen].get("error")
        ]
        out.append(
            f"<table><tr><th>metric</th>{head}</tr>{''.join(rows)}</table>"
            + "".join(errs)
        )
    return "\n".join(out)


def _hardware_row(hw: dict) -> dict[str, str]:
    """Flatten one tag's hardware snapshot to a small set of display fields."""
    runner = hw.get("runner", {})
    cluster = hw.get("cluster", {})
    row = {
        "runner cpu": f"{runner.get('cpu_model', '—')} ({runner.get('cpu_count', '—')} cores)",
        "runner mem": f"{runner.get('mem_total_gb', '—')} GB",
    }
    if cluster.get("error"):
        row["cluster"] = f"error: {cluster['error']}"
        return row
    nodes = cluster.get("nodes", [])
    if not nodes:
        return row
    row["cluster nodes"] = str(len(nodes))
    row["node cpu"] = ", ".join(str(n.get("cpu", "—")) for n in nodes)
    row["node mem"] = ", ".join(str(n.get("memory", "—")) for n in nodes)
    row["node gpus"] = ", ".join(str(n.get("gpus") or 0) for n in nodes)
    row["os image"] = nodes[0].get("os_image", "—")
    row["kubelet"] = nodes[0].get("kubelet_version", "—")
    return row


def _hardware_section(docs: dict[str, dict]) -> str:
    """One column per tag, so it's obvious whether a change in the numbers
    actually reflects different hardware rather than the code under test."""
    rows = {t: _hardware_row(d["hardware"]) for t, d in docs.items() if d.get("hardware")}
    if not rows:
        return ""
    fields = list(dict.fromkeys(f for r in rows.values() for f in r))
    head = "".join(f"<th>{html.escape(t)}</th>" for t in rows)
    body_rows = "".join(
        f"<tr><td>{html.escape(f)}</td>"
        + "".join(f"<td>{html.escape(rows[t].get(f, '—'))}</td>" for t in rows)
        + "</tr>"
        for f in fields
    )
    return f"<h2>hardware</h2><table><tr><th>field</th>{head}</tr>{body_rows}</table>"


def render(out_path: Path) -> Path:
    docs = store.load_all()
    if not docs:
        raise SystemExit(f"no stored results found in {store.RESULTS_DIR}")
    suites = list(dict.fromkeys(s for d in docs.values() for s in d["suites"]))
    body = [f"<h1>Kaapana platform benchmark</h1>",
            f"<div class='meta'>generated {time.strftime('%Y-%m-%d %H:%M')} — "
            f"tags: {html.escape(', '.join(docs))}</div>",
            _hardware_section(docs)]
    body += [_suite_section(s, docs) for s in suites]

    pngs = sorted(store.RESULTS_DIR.glob("compare_*.png"))
    if pngs:
        body.append("<h2>comparison heatmaps</h2>")
        for png in pngs:
            b64 = base64.b64encode(png.read_bytes()).decode()
            body.append(f"<h3>{html.escape(png.name)}</h3>"
                        f"<img src='data:image/png;base64,{b64}'>")

    out_path = Path(out_path)
    out_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Kaapana platform benchmark</title><style>{STYLE}</style></head>"
        f"<body>{''.join(body)}</body></html>"
    )
    return out_path
