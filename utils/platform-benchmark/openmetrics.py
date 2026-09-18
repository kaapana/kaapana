"""Render results as OpenMetrics text for GitLab's artifacts:reports:metrics."""

from __future__ import annotations

PREFIX = "kaapana"


def _sample(name: str, labels: dict[str, str], value: float) -> str:
    if labels:
        pairs = ",".join(f'{k}="{v}"' for k, v in labels.items())
        return f"{name}{{{pairs}}} {value}"
    return f"{name} {value}"


def _walk(suite: str, metrics: dict, labels: dict[str, str], out: dict[str, list[str]]) -> None:
    for key, value in metrics.items():
        if isinstance(value, dict):
            for item, inner in value.items():
                if isinstance(inner, (int, float)) and not isinstance(inner, bool):
                    name = f"{PREFIX}_{suite}_{key}"
                    out.setdefault(name, []).append(_sample(name, {**labels, "item": item}, inner))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            name = f"{PREFIX}_{suite}_{key}"
            out.setdefault(name, []).append(_sample(name, labels, value))


def render(results: dict) -> str:
    """results: {suite: {run: metrics}}, where metrics is flat or scenario -> metrics."""
    out: dict[str, list[str]] = {}
    for suite, per_run in results.items():
        for run, metrics in per_run.items():
            scenarios = metrics if all(isinstance(v, dict) for v in metrics.values()) else {None: metrics}
            for scenario, values in scenarios.items():
                labels = {"run": run}
                if scenario is not None:
                    labels["scenario"] = scenario
                _walk(suite, values, labels, out)
    lines = []
    for name, samples in out.items():
        lines.append(f"# TYPE {name} gauge")
        lines += samples
    lines.append("# EOF")
    return "\n".join(lines) + "\n"
