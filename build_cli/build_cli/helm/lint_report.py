import re
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from pathlib import Path

from build_cli.utils import get_logger

logger = get_logger()

UNIT_PATTERN = re.compile(r"^==> Linting (?P<unit>.+)$")
FINDING_PATTERN = re.compile(r"^\[(?P<level>WARNING|ERROR)\] (?P<message>.*)$")
FILE_PATTERN = re.compile(r"^(?P<file>[^\s:]+): (?P<detail>.*)$")
REDUNDANT_DETAIL = re.compile(r": metadata\.name: Invalid value| \(e\.g\.")


def parse_helm_lint(stdout: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    unit = "."
    for line in stdout.splitlines():
        unit_match = UNIT_PATTERN.match(line)
        if unit_match:
            unit = unit_match["unit"].strip()
            continue
        finding_match = FINDING_PATTERN.match(line)
        if finding_match:
            message = finding_match["message"]
            file_match = FILE_PATTERN.match(message)
            file = file_match["file"] if file_match else "Chart.yaml"
            if file.startswith("/"):
                file = "Chart.yaml"
            findings.append(
                {
                    "unit": unit,
                    "level": finding_match["level"],
                    "file": file,
                    "message": file_match["detail"] if file_match else message,
                }
            )
        elif findings and line.startswith((" ", "\t")) and line.strip():
            findings[-1]["message"] += f" {line.strip()}"
    for finding in findings:
        finding["message"] = REDUNDANT_DETAIL.split(finding["message"])[0]
    return findings


def rendered_location(render_dir: Path, path: Path) -> tuple[str, str]:
    if not path.is_relative_to(render_dir):
        return ".", str(path)
    parts = path.relative_to(render_dir).parts[1:]
    index = 0
    while len(parts) > index + 2 and parts[index] == "charts":
        index += 2
    return "/".join(parts[:index]) or ".", "/".join(parts[index:])


def write_junit_report(suite: str, cases: list[dict[str, str | None]], report_file: Path, system_err: str = "") -> None:
    failures = [case for case in cases if case.get("failure")]
    skipped = [case for case in cases if case.get("skipped")]
    counts = {"tests": str(len(cases)), "failures": str(len(failures)), "skipped": str(len(skipped))}
    root = ET.Element("testsuites", name=suite, **counts)
    testsuite = ET.SubElement(root, "testsuite", name=suite, **counts)
    for case in cases:
        testcase = ET.SubElement(testsuite, "testcase", classname=case["classname"] or "", name=case["name"] or "")
        if case.get("failure"):
            ET.SubElement(testcase, "failure", message=case["failure"]).text = case["failure"]
        elif case.get("skipped"):
            ET.SubElement(testcase, "skipped", message=case["skipped"])
    if system_err.strip():
        ET.SubElement(testsuite, "system-err").text = system_err.strip()
    ET.indent(root)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(ET.tostring(root, encoding="unicode"))


def finding_owner(finding: dict[str, str]) -> str:
    return finding["chart"] if finding["unit"] == "." else Path(finding["unit"]).name


def in_changed_charts(finding: dict[str, str], only_charts: AbstractSet[str] | None) -> bool:
    return only_charts is None or finding_owner(finding) in only_charts


def is_blocking(finding: dict[str, str], strict: bool, only_charts: AbstractSet[str] | None) -> bool:
    return strict and in_changed_charts(finding, only_charts)


def case_key(finding: dict[str, str]) -> tuple[str, str]:
    name = f"{finding['unit']}/{finding['file']}"
    if finding.get("resource"):
        name += f" {finding['resource']}"
    return finding["chart"], name


def lint_cases(
    findings: list[dict[str, str]],
    linted_charts: list[str],
    crashes: dict[str, str],
    ignored_charts: list[str],
) -> list[dict[str, str | None]]:
    failing_charts = {finding["chart"] for finding in findings} | set(crashes)
    failed: list[dict[str, str | None]] = [
        {
            "classname": case_key(finding)[0],
            "name": case_key(finding)[1],
            "failure": f"[{finding['level']}] {finding['message']}",
        }
        for finding in findings
    ]
    crashed: list[dict[str, str | None]] = [
        {"classname": chart, "name": "helm lint", "failure": message} for chart, message in crashes.items()
    ]
    skipped: list[dict[str, str | None]] = [
        {"classname": chart, "name": "helm lint", "skipped": "ignore_linting: true"} for chart in ignored_charts
    ]
    passed: list[dict[str, str | None]] = [
        {"classname": chart, "name": "helm lint", "failure": None}
        for chart in linted_charts
        if chart not in failing_charts and chart not in ignored_charts
    ]
    return failed + crashed + skipped + passed


def log_junit_report(report_file: Path, hidden: AbstractSet[tuple[str, str]] = frozenset(), note: str = "") -> None:
    root = ET.parse(report_file).getroot()
    cases = list(root.iter("testcase"))
    problems = [
        (case.get("classname") or "", case.get("name") or "", problem.get("message") or problem.text or "")
        for case in cases
        for problem in case
        if problem.tag in ("failure", "error")
    ]
    skipped = sum(case.find("skipped") is not None for case in cases)
    system_err = [line for element in root.iter("system-err") for line in (element.text or "").splitlines()]
    shown = [problem for problem in problems if problem[:2] not in hidden]
    log_problems(
        f"{report_file.name}: {len(cases)} checked, {len(problems)} failed, {skipped} skipped",
        shown,
        hidden_count=len(problems) - len(shown),
        note=note,
        extra_lines=system_err,
    )


def log_problems(
    title: str,
    shown: list[tuple[str, str, str]],
    hidden_count: int = 0,
    note: str = "",
    extra_lines: Sequence[str] = (),
) -> None:
    lines = [title]
    grouped: dict[str, list[str]] = {}
    for classname, name, message in shown:
        indented = message.replace("\n", "\n      ")
        grouped.setdefault(classname, []).append(f"    {name}: {indented}")
    for classname, entries in grouped.items():
        lines += [f"  {classname}", *entries]
    if hidden_count:
        lines.append(f"  {hidden_count} more not blocking (charts without changed files or advisory)")
    if note and (shown or hidden_count):
        lines.append(f"  {note}")
    lines += [f"  {line}" for line in extra_lines]
    (logger.warning if shown else logger.info)("\n".join(lines))

