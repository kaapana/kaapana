"""Summarising measurements and rendering them as markdown.

Timings are right-skewed, so the median carries everything here, not the mean.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist

from .model import NO_DIRECTION, Result

TARGET_PRECISION = 0.10


def coefficient_of_variation(values: list[float]) -> float | None:
    """Relative spread."""
    if len(values) < 2:
        return None
    mean = statistics.fmean(values)
    if mean == 0:
        return None
    return statistics.stdev(values) / mean


def repetitions_for_precision(cv: float | None, precision: float = 0.10,
                              confidence: float = 0.95) -> int:
    """n = (z * cv / precision)^2 — repetitions needed for a median within
    +/- precision of itself, from a spread already measured."""
    if not cv:
        return 1
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    return max(1, math.ceil((z * cv / precision) ** 2))


@dataclass(frozen=True)
class Summary:
    n: int
    median: float
    minimum: float
    maximum: float
    cv: float | None


def summarize(values: list[float]) -> Summary:
    return Summary(
        n=len(values),
        median=statistics.median(values),
        minimum=min(values),
        maximum=max(values),
        cv=coefficient_of_variation(values),
    )


def format_value(value: float, unit: str) -> str:
    if unit == "seconds":
        return f"{value * 1000:.0f}ms" if abs(value) < 1 else f"{value:,.1f}s"
    if unit == "bits_per_second":
        return f"{value / 1e6:,.1f} Mbit/s"
    return f"{value:g}"


def suggested_runs(metric, summary: Summary) -> str:
    """Only for measurements; counters keep their exact value however often
    they are repeated."""
    if metric.direction == NO_DIRECTION:
        return "-"
    return str(repetitions_for_precision(summary.cv, TARGET_PRECISION))


def format_spread(summary: Summary) -> str:
    if summary.n < 2:
        return "single run"
    spread = f"{summary.cv * 100:.1f}%" if summary.cv is not None else "-"
    return f"n={summary.n}, cv {spread}"


def _table(header: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_no data_\n"
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def _context_lines(context: dict) -> list[str]:
    code = context.get("code", {})
    dataset = context.get("dataset", {})
    nodes = context.get("cluster", {}).get("nodes", [])
    lines = [
        (f"- profile: `{context.get('profile', '?')}`, "
         f"host `{context.get('target', {}).get('host', '?')}`"),
        f"- code: `{code.get('branch', '?')}` @ `{str(code.get('commit', '?'))[:12]}`"
        + (" (dirty)" if code.get("dirty") else ""),
    ]
    if dataset.get("commit"):
        lines.append(f"- dataset: `{str(dataset['commit'])[:12]}` at `{dataset.get('path', '?')}`")
    if nodes:
        node = nodes[0]
        lines.append(
            f"- cluster: {len(nodes)} node(s), {node.get('cpu')} cpu, "
            f"{node.get('memory')} memory, {node.get('gpus')} gpu, kubelet {node.get('kubelet')}"
        )
    if context.get("ci", {}).get("job_url"):
        lines.append(f"- job: {context['ci']['job_url']}")
    return lines


def render_result(result: Result) -> str:
    out = ["# Kaapana platform benchmark", ""]
    out += _context_lines(result.context)
    policy = result.policy
    out += [
        "",
        (f"Repetitions: {policy.get('repeat')} measured, {policy.get('warmup')} warmup "
         f"(discarded). Summary statistic: median."),
        "",
        (f"`suggested runs` is what the observed spread implies for a median good to "
         f"+/-{TARGET_PRECISION * 100:.0f}%, from n = (1.96 * cv / "
         f"{TARGET_PRECISION:g})^2. Raise --repeat to that number for the scenarios "
         f"that ask for more."),
        "",
    ]

    for suite in dict.fromkeys(r.suite for r in result.records):
        out.append(f"## {suite}")
        rows = []
        for record in [r for r in result.records if r.suite == suite]:
            summary = summarize(record.values)
            invalid = result.invalid_reason(suite, record.case)
            rows.append([
                record.case,
                record.metric.name,
                format_value(summary.median, record.metric.unit),
                format_value(summary.minimum, record.metric.unit)
                + " - " + format_value(summary.maximum, record.metric.unit),
                format_spread(summary),
                suggested_runs(record.metric, summary),
                invalid or "",
            ])
        out.append(_table(
            ["case", "metric", "median", "range", "spread", "suggested runs", "invalid"],
            rows,
        ))
    return "\n".join(out)


def write(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path
