"""Tagged result storage: results/<tag>.json holds one document per platform
version with all suites that were run under that tag:

  {"tag": "...", "date": "...", "suites": {"ingest": {...}, "internet": {...}, "gpu": {...}},
   "hardware": {"runner": {...}, "cluster": {"nodes": [...]}}}
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

# ./results in the current working directory by default; override with
# BENCHMARK_RESULTS_DIR or the CLI's --results-dir
RESULTS_DIR = Path(os.environ.get("BENCHMARK_RESULTS_DIR", "results"))


def _read(path: Path) -> dict:
    doc = json.loads(path.read_text())
    if "suites" not in doc:  # legacy ingest-only schema {"results": {...}}
        doc["suites"] = {"ingest": doc.pop("results", {})}
    return doc


def load(tag: str) -> dict:
    return _read(RESULTS_DIR / f"{tag}.json")


def load_all() -> dict[str, dict]:
    """All stored tags, oldest first."""
    paths = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return {p.stem: _read(p) for p in paths}


def save(tag: str, suite: str, metrics: dict, force: bool = False,
         hardware: dict | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{tag}.json"
    doc = _read(path) if path.exists() else {"tag": tag, "suites": {}}
    if suite in doc["suites"] and not force:
        raise SystemExit(f"{path} already has a {suite!r} result — use --force to overwrite")
    doc["suites"][suite] = metrics
    doc["date"] = time.strftime("%Y-%m-%d %H:%M")
    if hardware is not None:
        doc["hardware"] = hardware
    path.write_text(json.dumps(doc, indent=2))
    return path


def print_comparison(suite: str) -> None:
    """Print the suite's metrics side by side for every stored tag."""
    docs = {t: d for t, d in load_all().items() if suite in d["suites"]}
    if not docs:
        return
    print(f"\n{'=' * 30} {suite}: all tags {'=' * 30}")
    if suite == "ingest":
        names = list(dict.fromkeys(k for d in docs.values() for k in d["suites"]["ingest"]))
        hdr = f"{'scenario':<14}" + "".join(f"{t:>22}" for t in docs)
        print(hdr + "\n" + "─" * len(hdr) + "   (run p50 / wall clock, s)")
        for name in names:
            row = f"{name:<14}"
            for d in docs.values():
                s = d["suites"]["ingest"].get(name)
                if not s or "run_p50_s" not in s:
                    row += f"{'error' if s else '—':>22}"
                else:
                    row += f"{s['run_p50_s']:>11.0f} /{s['wall_s']:>7.0f}s "
            print(row)
        for t, d in docs.items():
            fails = {n: s["failed_runs"] for n, s in d["suites"]["ingest"].items()
                     if s.get("failed_runs")}
            dropped = {n: s["dropped_series"] for n, s in d["suites"]["ingest"].items()
                       if s.get("dropped_series")}
            errors = [n for n, s in d["suites"]["ingest"].items() if "error" in s]
            if fails:
                print(f"  ⚠ {t} had failed runs: {fails}")
            if dropped:
                print(f"  ⚠ {t} had silently dropped series (no DAG run): {dropped}")
            if errors:
                print(f"  ⚠ {t} had failed scenarios: {errors}")
    else:
        metrics = list(next(iter(docs.values()))["suites"][suite].keys())
        hdr = f"{'metric':<16}" + "".join(f"{t:>16}" for t in docs)
        print(hdr + "\n" + "─" * len(hdr))
        for m in metrics:
            row = f"{m:<16}"
            for d in docs.values():
                row += f"{str(d['suites'][suite].get(m, '—')):>16}"
            print(row)
