"""Kaapana platform benchmark.

  benchmark run --suite ingest --host https://<instance> --password <pw> --data-dir <dir>
  benchmark run --suite internet --suite gpu --kubectl "ssh e230-pc11 microk8s kubectl"
  benchmark run --suite ingest --scenario max --runs 3 --out artifacts/benchmark

--out writes results.json and metrics.txt (OpenMetrics). --scenario-file holds
{root_path: "...", scenarios: {name: [directory, ...]}} — directories are
relative to --data-dir/root_path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import openmetrics
import typer
from suites import gpu as gpu_suite
from suites import helm as helm_suite
from suites import ingest as ingest_suite
from suites import internet as internet_suite

SUITES = ("ingest", "internet", "gpu", "helm")

app = typer.Typer(help=__doc__, add_completion=False, no_args_is_help=True)


def _has_failure(value) -> bool:
    if isinstance(value, dict):
        if value.get("error") or value.get("failed_scenario") or value.get("failed_runs"):
            return True
        return any(_has_failure(v) for v in value.values())
    return False


def _outcomes(results: dict) -> list[bool]:
    outcomes = []
    for runs in results.values():
        for items in runs.values():
            if isinstance(items, dict) and any(isinstance(v, dict) for v in items.values()):
                outcomes.extend(not _has_failure(item) for item in items.values())
            else:
                outcomes.append(not _has_failure(items))
    return outcomes


@app.callback()
def main() -> None:
    """Kaapana platform benchmark."""


@app.command()
def run(
    suite: List[str] = typer.Option(["ingest"], help=f"suites to run: {', '.join(SUITES)}"),
    runs: int = typer.Option(1, help="repetitions of every selected suite"),
    out: Optional[Path] = typer.Option(None, help="write results.json and metrics.txt here"),
    host: str = typer.Option("https://e230-pc11.inet.dkfz-heidelberg.de", help="platform URL (ingest)"),
    username: str = typer.Option("kaapana"),
    password: str = typer.Option("", help="platform password (ingest)"),
    data_dir: Optional[Path] = typer.Option(
        None, envvar="BENCHMARK_DATA_DIR", help="dataset repo root; scenario root_path is relative to this (ingest)"
    ),
    scenario_file: Optional[Path] = typer.Option(
        None, "--scenario-file", help="scenario definitions, JSON (required for the ingest suite)"
    ),
    scenario: List[str] = typer.Option([], help="scenarios to run (default: all in the file)"),
    timeout_h: float = typer.Option(4.0, help="how long to wait for a scenario's runs to finish"),
    dag_id: str = typer.Option("service-process-incoming-dcm"),
    reset: bool = typer.Option(True, "--reset/--no-reset", help="delete each scenario's series before upload"),
    kubectl: str = typer.Option("kubectl", help='kubectl entrypoint, e.g. "ssh host microk8s kubectl"'),
    helm_cmd: str = typer.Option("helm", "--helm", help='helm entrypoint, e.g. "ssh host microk8s helm"'),
    namespace: str = typer.Option("default", help="namespace for the internet/gpu pods"),
    gpu_seconds: int = typer.Option(60, help="gpu_burn stress duration"),
    proxy: Optional[str] = typer.Option(
        "http://www-int2.dkfz-heidelberg.de:80", help="HTTP proxy for the speedtest pod ('' to disable)"
    ),
) -> None:
    """Run the selected suites and report their metrics."""
    unknown = [s for s in suite if s not in SUITES]
    if unknown:
        raise typer.BadParameter(f"unknown suite(s) {unknown}; pick from {', '.join(SUITES)}")

    root_path = ""
    config: dict[str, list[str]] = {}
    names: list[str] = []
    if "ingest" in suite:
        if not data_dir:
            raise typer.BadParameter("--data-dir is required for the ingest suite")
        if not scenario_file:
            raise typer.BadParameter(
                "--scenario-file is required for the ingest suite: JSON with root_path and a "
                "scenarios map of name to the list of directories it sends, relative to "
                "--data-dir/root_path"
            )
        if not scenario_file.is_file():
            raise typer.BadParameter(f"no scenario file at {scenario_file}")
        root_path, config = ingest_suite.load(scenario_file)
        names = scenario or list(config)
        missing = [n for n in names if n not in config]
        if missing:
            raise typer.BadParameter(f"unknown scenario(s) {missing} in {scenario_file}")

    results: dict[str, dict[str, dict]] = {}
    for i in range(1, runs + 1):
        for name in suite:
            if name == "ingest":
                metrics = ingest_suite.run(
                    host,
                    username,
                    password,
                    dag_id,
                    data_dir,
                    root_path,
                    config,
                    names,
                    reset=reset,
                    timeout_s=int(timeout_h * 3600),
                )
            elif name == "internet":
                metrics = internet_suite.run(kubectl, namespace, proxy or None)
            elif name == "gpu":
                metrics = gpu_suite.run(kubectl, namespace, gpu_seconds)
            else:
                metrics = helm_suite.run(helm_cmd, kubectl)
            results.setdefault(name, {})[str(i)] = metrics

    typer.echo(json.dumps(results, indent=2))
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.json").write_text(json.dumps(results, indent=2))
        (out / "metrics.txt").write_text(openmetrics.render(results))
        typer.echo(f"wrote {out}/results.json and {out}/metrics.txt")

    outcomes = _outcomes(results)
    failed = outcomes.count(False)
    if failed:
        typer.echo(f"WARNING: {failed}/{len(outcomes)} item(s) failed", err=True)
        if failed == len(outcomes):
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
