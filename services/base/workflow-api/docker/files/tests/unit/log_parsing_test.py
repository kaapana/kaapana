"""Unit tests for Airflow log parsing (AirflowPluginAdapter.parse_task_run_logs).

Regression coverage for #2226: continuation lines without a log level (e.g.
Python traceback bodies) must not be dropped.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.adapters.adapters.airflow_adapter import AirflowPluginAdapter  # noqa: E402


@pytest.fixture
def adapter() -> AirflowPluginAdapter:
    # Bypass __init__ to avoid filesystem/env side effects; parse_task_run_logs
    # only relies on class-level regexes and the _parse_ts classmethod.
    return AirflowPluginAdapter.__new__(AirflowPluginAdapter)


def _wrap(log_text: str) -> str:
    # Airflow returns logs as a repr of [(host, log_text), ...].
    return repr([("worker-1", log_text)])


def test_traceback_lines_are_preserved(adapter):
    log_text = (
        "[2026-06-12T12:38:18.000+00:00] {taskinstance.py:3336} ERROR - Task failed with exception\n"
        "Traceback (most recent call last):\n"
        '  File "/opt/venv/.../taskinstance.py", line 771, in _execute_task\n'
        "    result = _execute_callable(context=context)\n"
        "pydantic_core._pydantic_core.ValidationError: 1 validation error for BaseEnv"
    )

    lines = adapter.parse_task_run_logs(_wrap(log_text))

    messages = [line.message for line in lines]
    assert len(lines) == 5
    assert "Traceback (most recent call last):" in messages
    assert any("pydantic_core" in m for m in messages)


def test_continuation_inherits_preceding_severity_and_timestamp(adapter):
    log_text = (
        "[2026-06-12T12:38:18.000+00:00] {taskinstance.py:3336} ERROR - boom\n"
        '  File "x.py", line 1, in <module>'
    )

    lines = adapter.parse_task_run_logs(_wrap(log_text))

    assert lines[1].severity == "ERROR"
    assert lines[1].time == lines[0].time


def test_leading_continuation_defaults_to_info(adapter):
    # A continuation line before any level-bearing line falls back to INFO.
    lines = adapter.parse_task_run_logs(_wrap("orphan line without level"))

    assert len(lines) == 1
    assert lines[0].severity == "INFO"
    assert lines[0].message == "orphan line without level"


def test_standard_lines_still_parse(adapter):
    log_text = (
        "[2026-06-12T12:38:18.000+00:00] {taskinstance.py:42} INFO - starting\n"
        "*** Reading local file: /logs/x.log\n"
        "WARNING - bare level line"
    )

    lines = adapter.parse_task_run_logs(_wrap(log_text))

    severities = [line.severity for line in lines]
    assert severities == ["INFO", "DEBUG", "WARNING"]
    assert lines[0].metadata == {"location": "taskinstance.py:42"}
