"""Command line interface.

  benchmark run --suite ingest --repeat 3 --data-dir <dir> --scenarios <file> --out-dir results
  benchmark report --result results/benchmark.json
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import model, provenance, report, suites

RESULT_FILE = "benchmark.json"
REPORT_FILE = "benchmark.md"

DEFAULT_REPEAT = 3
DEFAULT_WARMUP = 1


def build_target(args: argparse.Namespace) -> model.Target:
    password = os.environ.get("BENCHMARK_PASSWORD") or args.password
    if not password:
        raise SystemExit("set BENCHMARK_PASSWORD or pass --password")
    data_dir = Path(args.data_dir) if args.data_dir else None
    return model.Target(
        host=args.host,
        username=args.username,
        password=password,
        kubectl=args.kubectl,
        data_dir=data_dir,
        scenarios=resolve_scenarios(args.scenarios, data_dir),
    )


def resolve_scenarios(given: str | None, data_dir: Path | None) -> Path | None:
    """Explicit path wins, then a self-describing data repo.

    Resolved here so provenance records the same file the suite read.
    """
    if given:
        return Path(given)
    if data_dir:
        alongside = data_dir / suites.ingest.DEFAULT_SCENARIOS
        if alongside.is_file():
            return alongside
    return None


def measure(target: model.Target, suite_names: list[str], repeat: int,
            warmup: int) -> list[model.Record]:
    modules = [suites.get(name) for name in suite_names]

    for module in modules:
        for index in range(warmup):
            if hasattr(module, "warmup"):
                print(f"\n### warmup {index + 1}/{warmup}: {module.NAME}")
                module.warmup(target)

    records: list[model.Record] = []
    for module in modules:
        repetitions = []
        for index in range(repeat):
            print(f"\n### {module.NAME} repetition {index + 1}/{repeat}")
            repetitions.append(module.run(target))
        records += model.collect(module.NAME, repetitions)
    return records


def command_run(args: argparse.Namespace) -> int:
    target = build_target(args)
    out_dir = Path(args.out_dir)
    records = measure(target, args.suite, args.repeat, args.warmup)

    result = model.Result(
        context=provenance.collect(target, Path(args.repo), args.profile),
        policy={"repeat": args.repeat, "warmup": args.warmup, "suites": args.suite,
                "summary": "median"},
        records=records,
    )
    model.write(result, out_dir / RESULT_FILE)
    markdown = report.render_result(result)
    report.write(markdown, out_dir / REPORT_FILE)
    print("\n" + markdown)
    print(f"written to {out_dir}")
    return 0


def command_report(args: argparse.Namespace) -> int:
    result = model.read(Path(args.result))
    markdown = report.render_result(result)
    report.write(markdown, Path(args.out_dir) / REPORT_FILE)
    print(markdown)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="benchmark", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="measure a deployed platform")
    run.add_argument("--host", required=True, help="platform URL, e.g. https://my.instance")
    run.add_argument("--username", default="kaapana")
    run.add_argument("--password", default=None,
                     help="prefer the BENCHMARK_PASSWORD environment variable")
    run.add_argument("--kubectl", default="kubectl",
                     help='kubectl entrypoint, e.g. "ssh host microk8s kubectl"')
    run.add_argument("--data-dir", default=os.environ.get("BENCHMARK_DATA_DIR"),
                     help="dataset root the scenario paths are relative to")
    run.add_argument("--scenarios", default=None,
                     help="JSON file of scenario name -> {description, paths}; "
                          f"defaults to <data-dir>/{suites.ingest.DEFAULT_SCENARIOS}")
    run.add_argument("--suite", action="append", default=None,
                     choices=sorted(suites.SUITES), help="repeatable; defaults to ingest")
    run.add_argument("--repeat", type=int, default=DEFAULT_REPEAT,
                     help=f"measured repetitions (default {DEFAULT_REPEAT})")
    run.add_argument("--warmup", type=int, default=DEFAULT_WARMUP,
                     help=f"discarded repetitions first (default {DEFAULT_WARMUP})")
    run.add_argument("--out-dir", default="results")
    run.add_argument("--profile", default="workstation",
                     help="class of environment, recorded with the results")
    run.add_argument("--repo", default=".", help="repository to record the commit of")
    run.set_defaults(handler=command_run)

    show = commands.add_parser("report", help="re-render a stored result")
    show.add_argument("--result", required=True)
    show.add_argument("--out-dir", default="results")
    show.set_defaults(handler=command_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "suite", None) is None and args.command == "run":
        args.suite = ["ingest"]
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
