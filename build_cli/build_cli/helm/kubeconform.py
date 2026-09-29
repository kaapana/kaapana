import os
import shutil
import xml.etree.ElementTree as ET
from subprocess import PIPE, CompletedProcess, run
from typing import List

SCHEMA_LOCATIONS = (
    "default",
    "https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
)


def is_installed() -> bool:
    return shutil.which("kubeconform") is not None


def validate_manifests(manifests: str) -> CompletedProcess:
    command = ["kubeconform", "-strict", "-summary", "-output", "junit"]
    for location in SCHEMA_LOCATIONS:
        command += ["-schema-location", location]

    skip_kinds = os.environ.get("KUBECONFORM_SKIP_KINDS", "")
    if skip_kinds:
        command += ["-skip", skip_kinds]

    return run(
        [*command, "-"],
        input=manifests,
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True,
        timeout=300,
    )


def summarize(junit_xml: str) -> str:
    totals = ET.fromstring(junit_xml)
    return f"{totals.get('tests')} resources, {totals.get('failures')} invalid, {totals.get('disabled')} skipped"


def failures(junit_xml: str) -> List[str]:
    root = ET.fromstring(junit_xml)
    return [
        f"{case.get('classname')} {case.get('name')}: {problem.get('message') or problem.text}"
        for case in root.iter("testcase")
        for problem in (*case.findall("failure"), *case.findall("error"))
    ]
