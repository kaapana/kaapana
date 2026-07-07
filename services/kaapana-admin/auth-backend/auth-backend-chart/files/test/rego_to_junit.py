#!/usr/bin/env python3
"""Converts `opa test -f json` output into a JUnit XML report for GitLab's Pipeline/Tests view."""
import json
import sys
from xml.sax.saxutils import escape


def main(json_path: str, junit_path: str) -> None:
    with open(json_path) as f:
        results = json.load(f) or []

    failures = sum(1 for r in results if r.get("fail") or r.get("error"))
    cases = []
    for r in results:
        name = escape(f"{r['package']}.{r['name']}")
        time = r.get("duration", 0) / 1e9
        if r.get("error"):
            cases.append(
                f'<testcase name="{name}" time="{time:.6f}">'
                f'<error message="{escape(str(r["error"]))}"/></testcase>'
            )
        elif r.get("fail"):
            cases.append(f'<testcase name="{name}" time="{time:.6f}"><failure/></testcase>')
        else:
            cases.append(f'<testcase name="{name}" time="{time:.6f}"/>')

    with open(junit_path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(
            f'<testsuite name="rego_policy_tests" tests="{len(results)}" failures="{failures}">\n'
        )
        f.write("\n".join(cases))
        f.write("\n</testsuite>\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
