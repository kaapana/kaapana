"""Suite registry.

A suite is a module with a NAME, a run(target) -> list[Sample], and optionally
a warmup(target) for the state that has to be hot before measuring.
"""

from __future__ import annotations

from . import gpu, helm, ingest, internet

SUITES = {module.NAME: module for module in (ingest, internet, gpu, helm)}


def get(name: str):
    if name not in SUITES:
        raise SystemExit(f"unknown suite {name!r} — choose from {', '.join(SUITES)}")
    return SUITES[name]
