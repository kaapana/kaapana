"""Kaapana platform benchmark CLI.

  benchmark ingestion-pipeline --tag Version3 --password <pw> --data-dir <dir>
  benchmark internet --tag Version3 --kubectl "ssh e230-pc11 microk8s kubectl"
  benchmark gpu --tag Version3 --seconds 120
  benchmark compare Version1 Version2
  benchmark push Version3          # upload a stored tag to the package registry
  benchmark pull-all               # download every tag not already stored locally
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

import compare as compare_mod
import hardware
import store
from suites import gpu as gpu_suite
from suites import helm as helm_suite
from suites import ingest as ingest_suite
from suites import internet as internet_suite

app = typer.Typer(help=__doc__, add_completion=False, no_args_is_help=True)


@app.callback()
def main(
    results_dir: Optional[Path] = typer.Option(
        None, help="where tagged results are stored/read "
        "(default ./results, or BENCHMARK_RESULTS_DIR)"),
):
    if results_dir is not None:
        store.RESULTS_DIR = results_dir

TagOpt = typer.Option(None, help="store the result under results/<tag>.json for later comparison")
ForceOpt = typer.Option(False, help="overwrite an existing result of this suite under the same tag")
KubectlOpt = typer.Option("kubectl", help='kubectl entrypoint, e.g. "ssh e230-pc11 microk8s kubectl"')
NamespaceOpt = typer.Option("default", help="namespace to run the benchmark pod in")


def _finish(suite: str, metrics: dict, tag: Optional[str], force: bool,
            kubectl: str = "kubectl") -> None:
    typer.echo(json.dumps(metrics, indent=2))
    if tag:
        path = store.save(tag, suite, metrics, force=force, hardware=hardware.collect(kubectl))
        typer.echo(f"saved {path}")
    store.print_comparison(suite)


@app.command("ingestion-pipeline")
def ingestion_pipeline(
    password: str = typer.Option(..., prompt=True, hide_input=True),
    data_dir: Path = typer.Option(..., envvar="BENCHMARK_DATA_DIR",
                                  help=f"image_modalities repo root holding "
                                  f"{ingest_suite.CT_DIR}, {ingest_suite.SEG_DIR}, "
                                  f"{ingest_suite.RTSTRUCT_DIR}, {ingest_suite.SM_DIR}"),
    mode: str = typer.Option("all", help="single | medium | max | trickle | all — "
                             "1 series per modality, 15 in parallel, 40 in parallel "
                             "(2x the DAG's max_active_runs=20), or 5 slow senders "
                             "(10 instances per chunk, 5s pauses)"),
    all_modes: bool = typer.Option(False, "--all", help="run the full suite: "
                                   "all modes together (same as --mode all)"),
    host: str = typer.Option("https://e230-pc11.inet.dkfz-heidelberg.de"),
    username: str = typer.Option("kaapana"),
    dag_id: str = typer.Option("service-process-incoming-dcm"),
    no_reset: bool = typer.Option(False, help="skip deleting each scenario's series before upload"),
    kubectl: str = KubectlOpt,
    tag: Optional[str] = TagOpt,
    force: bool = ForceOpt,
):
    """Send a fixed DICOM scenario set and measure DAG timing via the public APIs."""
    if all_modes:
        mode = "all"
    if mode not in (*ingest_suite.MODES, "all"):
        raise typer.BadParameter(f"mode must be one of {', '.join((*ingest_suite.MODES, 'all'))}")
    metrics = ingest_suite.run(host, username, password, dag_id, data_dir,
                               mode=mode, reset=not no_reset)
    _finish("ingest", metrics, tag, force, kubectl=kubectl)


@app.command()
def internet(
    kubectl: str = KubectlOpt,
    namespace: str = NamespaceOpt,
    proxy: Optional[str] = typer.Option("http://www-int2.dkfz-heidelberg.de:80",
                                        help="HTTP proxy for the speedtest pod ('' to disable)"),
    tag: Optional[str] = TagOpt,
    force: bool = ForceOpt,
):
    """Run a speedtest pod on the instance's cluster (utils/internet-benchmark image)."""
    metrics = internet_suite.run(kubectl, namespace, proxy or None)
    _finish("internet", metrics, tag, force, kubectl=kubectl)


@app.command()
def gpu(
    kubectl: str = KubectlOpt,
    namespace: str = NamespaceOpt,
    seconds: int = typer.Option(60, help="gpu_burn stress duration"),
    tag: Optional[str] = TagOpt,
    force: bool = ForceOpt,
):
    """Run gpu_burn on all GPUs of the instance (utils/nvidia-benchmark.yaml image)."""
    metrics = gpu_suite.run(kubectl, namespace, seconds)
    _finish("gpu", metrics, tag, force, kubectl=kubectl)


@app.command()
def helm(
    helm_cmd: str = typer.Option("helm", "--helm", help='helm entrypoint, e.g. "microk8s helm"'),
    kubectl: str = KubectlOpt,
    namespace: str = typer.Option("benchmark-helm", help="dedicated namespace, deleted afterwards"),
    sizes: str = typer.Option("10,50,100", help="comma-separated chart sizes (3 objects each)"),
    replicas: int = typer.Option(0, help="replicas per Deployment (0 = API-only, no pods)"),
    timeout: int = typer.Option(600, help="helm --wait timeout per install, seconds"),
    tag: Optional[str] = TagOpt,
    force: bool = ForceOpt,
):
    """Time helm install/uninstall of increasingly big synthetic charts."""
    metrics = helm_suite.run(helm_cmd, kubectl, namespace,
                             [int(s) for s in sizes.split(",")], replicas, timeout)
    _finish("helm", metrics, tag, force, kubectl=kubectl)


@app.command()
def compare(base_tag: str, new_tag: str):
    """Render % change heatmaps (one per shared suite) between two stored tags."""
    for png in compare_mod.compare_tags(base_tag, new_tag):
        typer.echo(f"saved {png}")


@app.command()
def report(
    out: Path = typer.Option("benchmark_report.html", help="output HTML file"),
):
    """Write a self-contained HTML report of all stored tags (tables per
    suite/scenario plus any compare_*.png heatmaps, embedded)."""
    import report as report_mod

    typer.echo(f"saved {report_mod.render(out)}")


@app.command()
def push(tag: str):
    """Upload a stored tag's result to the GitLab generic package registry
    (CI_JOB_TOKEN in CI, GITLAB_TOKEN locally) so it survives past this runner."""
    import registry

    registry.push(tag)
    typer.echo(f"pushed {tag}")


@app.command()
def pull(
    tag: str,
    force: bool = typer.Option(False, help="overwrite an existing local copy"),
):
    """Download one tag's result from the registry into the local results dir."""
    import registry

    if registry.pull(tag, force=force):
        typer.echo(f"pulled {tag}")
    else:
        typer.echo(f"{tag} already present locally, or not found in the registry")


@app.command("pull-all")
def pull_all():
    """Download every tag not already present locally — hydrates compare/report
    with the full cross-MR history instead of just this runner's own results."""
    import registry

    fetched = registry.pull_all()
    typer.echo(f"pulled {len(fetched)} new tag(s): {', '.join(fetched) or '(none)'}")


if __name__ == "__main__":
    app()
