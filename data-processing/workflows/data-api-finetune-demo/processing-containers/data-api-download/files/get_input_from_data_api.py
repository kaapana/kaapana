"""Store-agnostic get-input task — thin wiring over the ``data_api`` library.

Reads a client-selected list of Data API entity IDs from ``INPUT_ENTITY_IDS`` and
materialises them on disk via the library's ``StorageClient`` (which resolves
coordinates through ``DataClient`` and unpacks the storage-api archive as
``<entity_id>/<files>``, with a completeness check).

Because workflow-api no longer contacts the Data API, the entity IDs are
constructed client-side. To preserve the workflow designer's guarantee, this task
re-applies the channel's ``INPUT_CONSTRAINT_QUERY`` (a Data API query tree shipped
by the DAG): every supplied ID must satisfy the constraint, else the task fails
loudly. It also re-checks ``INPUT_CARDINALITY`` (``single`` channels accept at
most one ID). All HTTP/tar/completeness logic lives in ``data_api``.
"""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

from data_api import DataClient, StorageClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data-api-download")


async def _validate_constraint(
    data: DataClient, entity_ids: list, constraint: dict
) -> None:
    """Fail loudly unless every supplied ID satisfies the designer constraint.

    Resolves ``AND(constraint, id in entity_ids)`` and requires the result to
    equal the input set — this also catches IDs that no longer exist.
    """
    logger.info(
        "Re-validating %d entity ID(s) against the channel constraint", len(entity_ids)
    )
    where = {
        "type": "group",
        "op": "and",
        "children": [
            constraint,
            {"type": "filter", "field": "id", "op": "in", "value": entity_ids},
        ],
    }
    matched = set(await data.query_index(where))
    rejected = [eid for eid in entity_ids if eid not in matched]
    if rejected:
        raise RuntimeError(
            f"{len(rejected)}/{len(entity_ids)} supplied entity IDs do not satisfy the "
            f"workflow constraint (or no longer exist): {rejected}"
        )


def _validate_cardinality(entity_ids: list, cardinality: str) -> None:
    """A ``single`` channel accepts at most one ID (0 allowed when optional)."""
    if cardinality == "single" and len(entity_ids) > 1:
        raise RuntimeError(
            f"Channel is single-cardinality but {len(entity_ids)} entity IDs were "
            f"supplied: {entity_ids}"
        )


async def _amain() -> None:
    # Imported here so the token machinery (kaapanapy/keycloak) is only needed at
    # runtime inside the container.
    from kaapanapy.helper import get_project_user_access_token

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("/home/kaapana/downloads")
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=int(os.environ.get("INPUT_DOWNLOAD_CONCURRENCY", "10") or "10"),
        help="Max entities downloaded concurrently (simultaneous storage-api connections)",
    )
    args = parser.parse_args()

    entity_ids = json.loads(os.environ.get("INPUT_ENTITY_IDS", "[]"))
    constraint_raw = os.environ.get("INPUT_CONSTRAINT_QUERY", "").strip()
    constraint = json.loads(constraint_raw) if constraint_raw else None
    cardinality = os.environ.get("INPUT_CARDINALITY", "multiple").strip() or "multiple"
    access_token = get_project_user_access_token()

    logger.info(
        "Resolved %d entity ID(s) from INPUT_ENTITY_IDS (cardinality=%s, constraint=%s)",
        len(entity_ids),
        cardinality,
        "yes" if constraint else "none",
    )
    _validate_cardinality(entity_ids, cardinality)

    if not entity_ids:
        logger.info("No entity IDs supplied — nothing to download.")

    async with DataClient(access_token=access_token) as data, StorageClient(
        access_token=access_token
    ) as storage:
        if constraint and entity_ids:
            await _validate_constraint(data, entity_ids, constraint)
        logger.info(
            "Downloading %d entity/-ies to %s (max_concurrency=%d)",
            len(entity_ids),
            args.output,
            args.max_concurrency,
        )
        await storage.download_entities(
            entity_ids,
            args.output,
            data_client=data,
            max_concurrency=args.max_concurrency,
        )
    logger.info(
        "Download complete: %d entity/-ies materialised under %s",
        len(entity_ids),
        args.output,
    )


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
