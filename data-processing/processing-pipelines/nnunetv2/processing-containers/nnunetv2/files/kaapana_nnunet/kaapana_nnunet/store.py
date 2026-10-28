"""Atomic publish / verified fetch of nnU-Net folders in a project S3 bucket.

S3 has no rename, so "complete" is defined by a marker object that is written last:

    publish:  upload every file to <root>/.staging/<id>/  ->  verify sizes
              ->  server-side copy to the final prefix  ->  write the marker  ->  drop staging
    fetch:    read the marker (missing = not published)  ->  download each listed file
              to a temporary name  ->  verify size + sha256  ->  rename into place

A marker lists every file of its unit with size and sha256, so readers never trust a
listing and never read partially written data. Several units can share one prefix
(e.g. fingerprint, plans and preprocessed data of one dataset), each with its own marker
``_DONE.<unit>.json``; the default unit has the marker ``_DONE.json``.
"""

import hashlib
import json
import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable, Optional, Union

from minio import Minio
from minio.commonconfig import CopySource
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

logger = logging.getLogger(__name__)

MARKER_VERSION = 1
STAGING_DIR = ".staging"
_UNIT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_CHUNK = 8 * 1024 * 1024


class StoreError(Exception):
    pass


class NotPublished(StoreError):
    pass


class AlreadyPublished(StoreError):
    pass


class IntegrityError(StoreError):
    pass


def sha256_file(path: Union[str, Path]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _retry(fn, attempts: int = 4, delay: float = 2.0):
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except (S3Error, OSError) as e:
            # 4xx answers (except throttling) will not get better by retrying
            if isinstance(e, S3Error) and e.code not in ("SlowDown", "InternalError", "ServiceUnavailable"):
                raise
            if attempt == attempts:
                raise
            logger.warning("S3 call failed (%s), retry %d/%d", e, attempt, attempts - 1)
            time.sleep(delay * attempt)


def _clean_rel(rel: str) -> str:
    rel = Path(rel).as_posix().lstrip("/")
    if not rel or rel == "." or ".." in Path(rel).parts:
        raise StoreError(f"invalid relative path: {rel!r}")
    return rel


class S3Store:
    def __init__(
        self,
        client: Union[Minio, Callable[[], Minio]],
        bucket: str,
        root: str = "nnunet",
        workers: int = 8,
    ):
        # a callable lets long running pods refresh expiring STS credentials
        self._client = client if callable(client) and not isinstance(client, Minio) else (lambda: client)
        self.bucket = bucket
        self.root = root.strip("/")
        self.workers = workers

    # ---------- keys ----------

    def key(self, prefix: str, rel: str = "") -> str:
        parts = [self.root, prefix.strip("/")]
        if rel:
            parts.append(_clean_rel(rel))
        return "/".join(p for p in parts if p)

    @staticmethod
    def marker_name(unit: Optional[str] = None) -> str:
        if unit is None:
            return "_DONE.json"
        if not _UNIT_RE.match(unit):
            raise StoreError(f"invalid unit name: {unit!r}")
        return f"_DONE.{unit}.json"

    def marker_key(self, prefix: str, unit: Optional[str] = None) -> str:
        return self.key(prefix, self.marker_name(unit))

    # ---------- markers ----------

    def read_marker(self, prefix: str, unit: Optional[str] = None) -> dict:
        key = self.marker_key(prefix, unit)
        try:
            resp = _retry(lambda: self._client().get_object(self.bucket, key))
        except S3Error as e:
            if e.code in ("NoSuchKey", "NoSuchObject"):
                raise NotPublished(f"s3://{self.bucket}/{key} does not exist - not (completely) published") from e
            raise
        try:
            return json.loads(resp.read())
        finally:
            resp.close()
            resp.release_conn()

    def read_json(self, prefix: str, rel: str) -> dict:
        """One small published JSON file, e.g. a plans file (no verification, use fetch for data)."""
        resp = _retry(lambda: self._client().get_object(self.bucket, self.key(prefix, rel)))
        try:
            return json.loads(resp.read())
        finally:
            resp.close()
            resp.release_conn()

    def is_published(self, prefix: str, unit: Optional[str] = None) -> bool:
        try:
            self.read_marker(prefix, unit)
            return True
        except NotPublished:
            return False

    def list_markers(self, prefix: str = "") -> list[dict]:
        """All complete units below ``prefix`` as {prefix, unit, marker}."""
        out = []
        base = self.key(prefix) + "/"
        for obj in self._client().list_objects(self.bucket, prefix=base, recursive=True):
            name = obj.object_name.rsplit("/", 1)[-1]
            if not (name.startswith("_DONE") and name.endswith(".json")):
                continue
            if f"/{STAGING_DIR}/" in "/" + obj.object_name:
                continue
            unit_prefix = obj.object_name.rsplit("/", 1)[0][len(self.root) + 1 :]
            unit = None if name == "_DONE.json" else name[len("_DONE.") : -len(".json")]
            try:
                marker = self.read_marker(unit_prefix, unit)
            except NotPublished:
                continue  # removed between list and read
            out.append({"prefix": unit_prefix, "unit": unit, "marker": marker})
        return out

    # ---------- publish ----------

    def publish(
        self,
        local_dir: Union[str, Path],
        prefix: str,
        files: Optional[Iterable[str]] = None,
        unit: Optional[str] = None,
        meta: Optional[dict] = None,
        overwrite: bool = False,
    ) -> dict:
        """Upload ``files`` (relative to ``local_dir``; directories are expanded, default: everything)
        to ``<root>/<prefix>/`` and mark the unit complete. Returns the marker."""
        local_dir = Path(local_dir)
        rels = self._expand(local_dir, files)
        if not rels:
            raise StoreError(f"nothing to publish in {local_dir}")
        marker_key = self.marker_key(prefix, unit)
        if self.is_published(prefix, unit) and not overwrite:
            raise AlreadyPublished(f"s3://{self.bucket}/{marker_key} already exists")

        publish_id = uuid.uuid4().hex
        staging = f"{self.root}/{STAGING_DIR}/{publish_id}"
        logger.info("publishing %d files to s3://%s/%s (unit %s)", len(rels), self.bucket, self.key(prefix), unit)

        def stage(rel):
            path = local_dir / rel
            size = path.stat().st_size
            digest = sha256_file(path)
            key = f"{staging}/{rel}"
            _retry(lambda: self._client().fput_object(self.bucket, key, str(path)))
            remote = self._client().stat_object(self.bucket, key)
            if remote.size != size:
                raise IntegrityError(f"staged {key} has {remote.size} bytes, local file has {size}")
            if path.stat().st_size != size or sha256_file(path) != digest:
                raise IntegrityError(f"{path} changed while it was uploaded")
            return {"path": rel, "size": size, "sha256": digest}

        try:
            with ThreadPoolExecutor(self.workers) as pool:
                entries = list(pool.map(stage, rels))

            if overwrite:
                # readers must never see the old marker next to new files
                self._client().remove_object(self.bucket, marker_key)

            def move(rel):
                _retry(
                    lambda: self._client().copy_object(
                        self.bucket, self.key(prefix, rel), CopySource(self.bucket, f"{staging}/{rel}")
                    )
                )

            with ThreadPoolExecutor(self.workers) as pool:
                list(pool.map(move, rels))

            marker = {
                "version": MARKER_VERSION,
                "id": publish_id,
                "unit": unit,
                "created": datetime.now(timezone.utc).isoformat(),
                "meta": meta or {},
                "files": entries,
            }
            self._put_json(marker_key, marker)
        finally:
            self._remove_prefix(staging + "/")
        return marker

    @staticmethod
    def _expand(local_dir: Path, files: Optional[Iterable[str]]) -> list[str]:
        if files is None:
            files = ["."]
        rels = set()
        for f in files:
            path = local_dir / f
            if path.is_dir():
                rels.update(p.relative_to(local_dir).as_posix() for p in path.rglob("*") if p.is_file())
            elif path.is_file():
                rels.add(_clean_rel(f))
            else:
                raise StoreError(f"{path} does not exist")
        return sorted(rels)

    def _put_json(self, key: str, data: dict):
        payload = json.dumps(data, indent=1).encode()
        _retry(
            lambda: self._client().put_object(
                self.bucket, key, BytesIO(payload), len(payload), content_type="application/json"
            )
        )

    # ---------- fetch ----------

    def fetch(
        self,
        prefix: str,
        local_dir: Union[str, Path],
        unit: Optional[str] = None,
        include: Optional[Callable[[str], bool]] = None,
    ) -> dict:
        """Download a published unit to ``local_dir`` and verify every file.
        Files that already exist locally with the right checksum are kept."""
        local_dir = Path(local_dir)
        marker = self.read_marker(prefix, unit)
        entries = [e for e in marker["files"] if include is None or include(e["path"])]

        def get(entry):
            dest = local_dir / _clean_rel(entry["path"])
            if dest.is_file() and dest.stat().st_size == entry["size"] and sha256_file(dest) == entry["sha256"]:
                return
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(f".{dest.name}.part-{uuid.uuid4().hex[:8]}")
            try:
                _retry(lambda: self._client().fget_object(self.bucket, self.key(prefix, entry["path"]), str(tmp)))
                if tmp.stat().st_size != entry["size"] or sha256_file(tmp) != entry["sha256"]:
                    raise IntegrityError(
                        f"s3://{self.bucket}/{self.key(prefix, entry['path'])} does not match its marker "
                        "(changed or republished while downloading?)"
                    )
                os.replace(tmp, dest)
            finally:
                tmp.unlink(missing_ok=True)

        with ThreadPoolExecutor(self.workers) as pool:
            list(pool.map(get, entries))

        if self.read_marker(prefix, unit)["id"] != marker["id"]:
            raise IntegrityError(f"{self.marker_key(prefix, unit)} was republished while downloading, retry")
        return marker

    def adopt(
        self, prefix: str, unit: Optional[str] = None, meta: Optional[dict] = None, ignore=(".reserved",)
    ) -> dict:
        """Mark files that were uploaded by hand (e.g. with the MinIO browser) as a complete unit.
        Every object is downloaded and hashed; the listing must not change meanwhile (upload still running?)."""
        base = self.key(prefix) + "/"

        def listing():
            return {
                o.object_name[len(base) :]: (o.size, o.etag)
                for o in self._client().list_objects(self.bucket, prefix=base, recursive=True)
                if not o.object_name[len(base) :].rsplit("/", 1)[-1].startswith("_DONE")
                and o.object_name[len(base) :] not in ignore
            }

        before = listing()
        if not before:
            raise NotPublished(f"s3://{self.bucket}/{base} is empty")

        def entry(rel):
            h = hashlib.sha256()
            resp = _retry(lambda: self._client().get_object(self.bucket, base + rel))
            try:
                for chunk in resp.stream(_CHUNK):
                    h.update(chunk)
            finally:
                resp.close()
                resp.release_conn()
            return {"path": _clean_rel(rel), "size": before[rel][0], "sha256": h.hexdigest()}

        with ThreadPoolExecutor(self.workers) as pool:
            entries = list(pool.map(entry, sorted(before)))
        if listing() != before:
            raise IntegrityError(f"s3://{self.bucket}/{base} changed while it was registered (upload still running?)")
        marker = {
            "version": MARKER_VERSION,
            "id": uuid.uuid4().hex,
            "unit": unit,
            "created": datetime.now(timezone.utc).isoformat(),
            "meta": {"adopted": True, **(meta or {})},
            "files": entries,
        }
        self._put_json(self.marker_key(prefix, unit), marker)
        return marker

    # ---------- delete / housekeeping ----------

    def delete(self, prefix: str, unit: Optional[str] = None):
        """Unpublish a unit: drop its marker first, then the files no other unit of the prefix uses."""
        marker = self.read_marker(prefix, unit)
        self._client().remove_object(self.bucket, self.marker_key(prefix, unit))
        still_used = set()
        for other in self.list_markers(prefix):
            if other["prefix"] == prefix.strip("/"):
                still_used.update(e["path"] for e in other["marker"]["files"])
        keys = [self.key(prefix, e["path"]) for e in marker["files"] if e["path"] not in still_used]
        self._remove_keys(keys)

    def cleanup_staging(self, older_than: timedelta = timedelta(days=8)):
        """Remove staging leftovers of crashed publishes. The default exceeds the longest workflow timeout."""
        limit = datetime.now(timezone.utc) - older_than
        stale = [
            obj.object_name
            for obj in self._client().list_objects(self.bucket, prefix=f"{self.root}/{STAGING_DIR}/", recursive=True)
            if obj.last_modified and obj.last_modified < limit
        ]
        self._remove_keys(stale)

    def _remove_prefix(self, prefix: str):
        try:
            keys = [o.object_name for o in self._client().list_objects(self.bucket, prefix=prefix, recursive=True)]
            self._remove_keys(keys)
        except S3Error as e:
            logger.warning("could not remove s3://%s/%s: %s", self.bucket, prefix, e)

    def _remove_keys(self, keys: list[str]):
        for start in range(0, len(keys), 1000):
            errors = self._client().remove_objects(self.bucket, [DeleteObject(k) for k in keys[start : start + 1000]])
            for err in errors:
                logger.warning("could not delete %s: %s", err.name, err.message)
