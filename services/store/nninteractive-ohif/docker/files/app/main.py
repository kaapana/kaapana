import base64
import hashlib
import json
import logging
import math
import os
import tempfile
import threading
import time
import uuid
import zlib
from dataclasses import dataclass, field
from email.parser import BytesParser
from email.policy import default
from typing import Any

import numpy as np
import pydicom
import requests
import SimpleITK as sitk
import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from nnInteractive.inference.remote import (
    ServerAtCapacityError,
    SessionExpiredError,
    nnInteractiveRemoteInferenceSession,
)
from skimage.draw import polygon2mask

logger = logging.getLogger("nninteractive-proxy")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

DICOMWEB_ROOT = os.environ.get(
    "DICOMWEB_ROOT",
    "http://dicom-web-filter-service.services.svc:8080",
).rstrip("/")
NNINTERACTIVE_SERVER_URL = os.environ.get(
    "NNINTERACTIVE_SERVER_URL",
    "http://nninteractive-server-service.services.svc:1527",
).rstrip("/")
NNINTERACTIVE_API_KEY = os.environ.get("NN_INTERACTIVE_API_KEY") or None
# Keep at or below the server's --max-sessions so a full proxy answers "busy" instead of the
# server rejecting a session the proxy thinks it can hold.
MAX_CACHED_SESSIONS = int(os.environ.get("MAX_CACHED_SESSIONS", "3"))
# A session whose browser has not sent a heartbeat (every 20 s) for this long is abandoned.
STALE_SESSION_SECONDS = float(os.environ.get("STALE_SESSION_SECONDS", "120"))
# A raw uint8 mask is one byte per voxel; this bounds what a single upload may occupy in memory.
MAX_MASK_UPLOAD_BYTES = int(os.environ.get("MAX_MASK_UPLOAD_BYTES", str(1024**3)))
REQUEST_TIMEOUT = float(os.environ.get("DICOMWEB_REQUEST_TIMEOUT", "120"))

app = FastAPI(title="OHIF nnInteractive proxy", version="0.1.0")


@dataclass
class SeriesSession:
    key: str
    series_uid: str
    session: nnInteractiveRemoteInferenceSession
    target_buffer: np.ndarray
    flipped: bool
    # Voxel spacing in [z, y, x]; napari scales its scribble brush by it.
    spacing_zyx: tuple[float, float, float] = (1.0, 1.0, 1.0)
    prompts_seen: set[str] = field(default_factory=set)
    prompt_order: list[str] = field(default_factory=list)
    last_used: float = field(default_factory=time.time)
    last_browser_seen: float = field(default_factory=time.time)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)


@dataclass
class CachedImage:
    image_4d: np.ndarray
    # SOPInstanceUIDs of the first and last slice of image_4d (SimpleITK's position order).
    first_sop: str
    last_sop: str
    # Fallback flip for clients that do not send their slice order: InstanceNumber descending.
    instance_number_flipped: bool
    timings: dict[str, float]
    spacing_zyx: tuple[float, float, float] = (1.0, 1.0, 1.0)
    last_used: float = field(default_factory=time.time)


sessions: dict[str, SeriesSession] = {}
sessions_lock = threading.RLock()
init_locks: dict[str, threading.Lock] = {}
image_cache: dict[str, CachedImage] = {}
image_cache_lock = threading.RLock()
image_locks: dict[str, threading.Lock] = {}
MAX_CACHED_IMAGES = int(os.environ.get("MAX_CACHED_IMAGES", "2"))


def _jsonish(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (list, dict, bool, int, float)):
        return value
    text = str(value)
    if text == "":
        return default
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _as_list(value: Any) -> list:
    parsed = _jsonish(value, [])
    return parsed if isinstance(parsed, list) else []


def _prompt_key(kind: str, prompt: Any) -> str:
    return f"{kind}:{json.dumps(prompt, sort_keys=True, separators=(',', ':'))}"


def _client_session_id(value: Any) -> str:
    parsed = _jsonish(value, "")
    text = "" if parsed is None else str(parsed).strip()
    if not text:
        raise HTTPException(400, "Missing required parameter: clientSessionID")
    return text


def _access_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization") or ""
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return request.headers.get("x-forwarded-access-token") or None


def _token_subject(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        subject = claims.get("sub")
        return str(subject) if subject else None
    except Exception:
        return None


def _principal(request: Request) -> str:
    """Who a session belongs to: the token subject plus the project scope.

    traefik's auth-check has already authenticated the token, and dicom-web-filter verifies it
    again whenever a session is created (see _assert_series_access), so the subject is only
    decoded here to keep users' sessions apart.
    """
    token = _access_token(request)
    if token:
        subject = _token_subject(token) or hashlib.sha256(token.encode()).hexdigest()[:16]
    else:
        subject = "anonymous"
    return f"{subject}|{request.headers.get('project') or ''}"


def _session_key(principal: str, study_uid: str, series_uid: str, client_session_id: str) -> str:
    return f"{principal}|{study_uid}|{series_uid}|{client_session_id}"


def _image_key(study_uid: str, series_uid: str) -> str:
    return f"{study_uid}|{series_uid}"


def _auth() -> tuple[str, str] | None:
    username = os.environ.get("DICOMWEB_USERNAME")
    password = os.environ.get("DICOMWEB_PASSWORD")
    return (username, password) if username and password else None


def _dicomweb_get(
    path: str,
    headers: dict[str, str] | None = None,
    accept: str = 'multipart/related; type="application/dicom"; transfer-syntax=*',
) -> requests.Response:
    url = f"{DICOMWEB_ROOT}/{path.lstrip('/')}"
    request_headers = {"Accept": accept}
    if headers:
        request_headers.update(headers)
    response = requests.get(
        url,
        headers=request_headers,
        auth=_auth(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response


def _multipart_payloads(content_type: str, body: bytes) -> list[bytes]:
    if "multipart/" not in content_type.lower():
        return [body]
    message = BytesParser(policy=default).parsebytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + body
    )
    payloads = []
    for part in message.iter_parts():
        if part.get_content_type().lower() == "application/dicom":
            payload = part.get_payload(decode=True)
            if payload:
                payloads.append(payload)
    return payloads


def _fetch_series_to_tempdir(
    study_uid: str,
    series_uid: str,
    tempdir: str,
    headers: dict[str, str] | None,
) -> list[str]:
    response = _dicomweb_get(f"studies/{study_uid}/series/{series_uid}", headers)
    payloads = _multipart_payloads(response.headers.get("Content-Type", ""), response.content)
    if not payloads:
        raise HTTPException(502, "DICOMweb response did not contain DICOM instances")

    files = []
    for index, payload in enumerate(payloads):
        path = os.path.join(tempdir, f"{index:06d}.dcm")
        with open(path, "wb") as f:
            f.write(payload)
        files.append(path)
    return files


def _load_image(
    study_uid: str,
    series_uid: str,
    headers: dict[str, str] | None,
) -> tuple[np.ndarray, str, str, bool, dict[str, float], tuple[float, float, float]]:
    timings: dict[str, float] = {}
    with tempfile.TemporaryDirectory(prefix="nninteractive-proxy-") as tempdir:
        fetch_start = time.time()
        _fetch_series_to_tempdir(study_uid, series_uid, tempdir, headers)
        timings["dicomweb_fetch"] = time.time() - fetch_start

        sitk_series_start = time.time()
        reader = sitk.ImageSeriesReader()
        series_ids = reader.GetGDCMSeriesIDs(tempdir)
        if not series_ids:
            raise HTTPException(502, "SimpleITK could not identify a DICOM series")
        files = list(reader.GetGDCMSeriesFileNames(tempdir, series_ids[0]))
        timings["sitk_series"] = time.time() - sitk_series_start

        sitk_execute_start = time.time()
        reader.SetFileNames(files)
        image = reader.Execute()
        timings["sitk_execute"] = time.time() - sitk_execute_start

        first = pydicom.dcmread(files[0], stop_before_pixels=True, force=True)
        last = pydicom.dcmread(files[-1], stop_before_pixels=True, force=True)
        instance_number_flipped = False
        if len(files) >= 2:
            try:
                second = pydicom.dcmread(files[1], stop_before_pixels=True, force=True)
                instance_number_flipped = int(first.get("InstanceNumber", 0)) > int(second.get("InstanceNumber", 0))
            except Exception:
                logger.warning("Could not determine slice flip from InstanceNumber", exc_info=True)

        numpy_start = time.time()
        volume = sitk.GetArrayFromImage(image)
        volume_4d = np.ascontiguousarray(volume[None])
        timings["numpy_convert"] = time.time() - numpy_start
        return (
            volume_4d,
            str(first.get("SOPInstanceUID", "")),
            str(last.get("SOPInstanceUID", "")),
            instance_number_flipped,
            timings,
            tuple(float(s) for s in image.GetSpacing()[::-1]),
        )


def _new_remote_session(
    image_4d: np.ndarray,
) -> tuple[nnInteractiveRemoteInferenceSession, np.ndarray, dict[str, float]]:
    timings: dict[str, float] = {}
    create_start = time.time()
    session = nnInteractiveRemoteInferenceSession(
        server_url=NNINTERACTIVE_SERVER_URL,
        api_key=NNINTERACTIVE_API_KEY,
        connect_timeout=10,
        read_timeout=float(os.environ.get("NNINTERACTIVE_READ_TIMEOUT", "120")),
        set_image_read_timeout=float(os.environ.get("NNINTERACTIVE_SET_IMAGE_TIMEOUT", "900")),
        write_timeout=float(os.environ.get("NNINTERACTIVE_WRITE_TIMEOUT", "300")),
    )
    timings["remote_create"] = time.time() - create_start

    set_image_start = time.time()
    session.set_image(image_4d)
    timings["remote_set_image"] = time.time() - set_image_start

    target_start = time.time()
    target_buffer = np.zeros(image_4d.shape[1:], dtype=np.uint8)
    session.set_target_buffer(target_buffer)
    timings["remote_set_target"] = time.time() - target_start
    return session, target_buffer, timings


def _keyed_lock(locks: dict[str, threading.Lock], guard: threading.RLock, key: str) -> threading.Lock:
    """The lock serializing one slow load (image fetch, session init) per key."""
    with guard:
        return locks.setdefault(key, threading.Lock())


def _evict_images_if_needed() -> None:
    while len(image_cache) > MAX_CACHED_IMAGES:
        oldest_key = min(image_cache, key=lambda k: image_cache[k].last_used)
        image_cache.pop(oldest_key, None)


def _assert_series_access(study_uid: str, series_uid: str, headers: dict[str, str] | None) -> None:
    """The image cache is shared, so a cache hit must not skip the caller's access check."""
    response = _dicomweb_get(
        f"studies/{study_uid}/series?SeriesInstanceUID={series_uid}",
        headers,
        accept="application/dicom+json",
    )
    if response.status_code == 204 or not response.content or not response.json():
        raise HTTPException(404, "Series not found")


def _get_cached_image(
    study_uid: str,
    series_uid: str,
    dicomweb_headers: dict[str, str] | None,
) -> CachedImage:
    key = _image_key(study_uid, series_uid)

    def cache_hit() -> CachedImage | None:
        with image_cache_lock:
            cached = image_cache.get(key)
        if cached is not None:
            _assert_series_access(study_uid, series_uid, dicomweb_headers)
            cached.last_used = time.time()
        return cached

    cached = cache_hit()
    if cached is not None:
        return cached

    with _keyed_lock(image_locks, image_cache_lock, key):
        cached = cache_hit()
        if cached is not None:
            return cached

        # Fetching the series through dicom-web-filter with the caller's token is the access check.
        volume_4d, first_sop, last_sop, instance_number_flipped, timings, spacing_zyx = _load_image(
            study_uid, series_uid, dicomweb_headers
        )
        loaded = CachedImage(
            volume_4d, first_sop, last_sop, instance_number_flipped, timings, spacing_zyx=spacing_zyx
        )
        with image_cache_lock:
            image_cache[key] = loaded
            _evict_images_if_needed()
        return loaded


def _resolve_flip(image: CachedImage, client_first_sop: str | None) -> bool:
    """Whether the viewer's slice order is the reverse of image_4d's.

    The viewer sends the SOPInstanceUID of its first slice. OHIF orders slices by position, which
    does not follow InstanceNumber for every series, so the InstanceNumber guess is only a fallback.
    """
    if not client_first_sop:
        logger.warning("Client sent no firstSOPInstanceUID; guessing slice order from InstanceNumber")
        return image.instance_number_flipped
    if client_first_sop == image.first_sop:
        return False
    if client_first_sop == image.last_sop:
        return True
    raise HTTPException(422, "Viewer slice order does not match the series volume")


def _validate_shape(image: CachedImage, client_shape: Any) -> None:
    """The viewer's [slices, rows, columns] must match the volume, or prompts land elsewhere."""
    shape = _jsonish(client_shape, None)
    if not shape:
        return
    if [int(v) for v in shape] != [int(v) for v in image.image_4d.shape[1:]]:
        raise HTTPException(
            422,
            f"Viewer volume {list(shape)} does not match the series volume {list(image.image_4d.shape[1:])}",
        )


def _reserve_capacity() -> None:
    """Free abandoned sessions, then refuse (never evict an active user) if still full."""
    now = time.time()
    with sessions_lock:
        stale = [
            entry
            for entry in sessions.values()
            if now - max(entry.last_browser_seen, entry.last_used) > STALE_SESSION_SECONDS
        ]
        for entry in stale:
            sessions.pop(entry.key, None)
        full = len(sessions) >= MAX_CACHED_SESSIONS
    # Close outside the global lock: closing talks to the server and may wait on an inference.
    for entry in stale:
        logger.info("Closing abandoned nnInteractive session for %s", entry.series_uid)
        _close_session_quietly(entry)
    if full:
        raise HTTPException(503, "All nnInteractive slots are in use; try again later")


def _close_session_quietly(entry: SeriesSession) -> None:
    try:
        with entry.lock:
            entry.session.close()
    except Exception:
        logger.warning("Failed to close nnInteractive session", exc_info=True)


def _touch_session(key: str) -> SeriesSession | None:
    """The live session for `key`, marked as just used."""
    with sessions_lock:
        entry = sessions.get(key)
        if entry is not None:
            entry.last_used = time.time()
        return entry


def _get_series_session(
    principal: str,
    study_uid: str,
    series_uid: str,
    client_session_id: str,
    dicomweb_headers: dict[str, str] | None,
    client_first_sop: str | None,
    client_shape: Any,
) -> SeriesSession:
    key = _session_key(principal, study_uid, series_uid, client_session_id)
    existing = _touch_session(key)
    if existing is not None:
        return existing

    with _keyed_lock(init_locks, sessions_lock, key):
        existing = _touch_session(key)
        if existing is not None:
            return existing

        _reserve_capacity()
        try:
            load_start = time.time()
            image = _get_cached_image(study_uid, series_uid, dicomweb_headers)
            image_4d, load_timings = image.image_4d, image.timings
            _validate_shape(image, client_shape)
            flipped = _resolve_flip(image, client_first_sop)
            session, target_buffer, remote_timings = _new_remote_session(image_4d)
            total = time.time() - load_start
            timings = {**load_timings, **remote_timings}
            logger.info(
                (
                    "Initialized nnInteractive session for %s client=%s in %.3fs; "
                    "image shape=%s flipped=%s timings=%s"
                ),
                series_uid,
                client_session_id,
                total,
                image_4d.shape,
                flipped,
                ", ".join(f"{key}={value:.3f}s" for key, value in timings.items()),
            )
        except HTTPException:
            raise
        except ServerAtCapacityError as e:
            raise HTTPException(503, "nnInteractive server is at capacity") from e
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (401, 403, 404):
                raise HTTPException(404, "Series not found") from e
            logger.exception("DICOMweb request failed for %s", series_uid)
            raise HTTPException(502, "DICOMweb request failed") from e
        except Exception as e:
            logger.exception("Could not initialize nnInteractive session for %s", series_uid)
            raise HTTPException(502, "Could not initialize nnInteractive session") from e

        entry = SeriesSession(key, series_uid, session, target_buffer, flipped, spacing_zyx=image.spacing_zyx)
        with sessions_lock:
            sessions[key] = entry
        return entry


def _close_entry(entry: SeriesSession) -> None:
    with sessions_lock:
        sessions.pop(entry.key, None)
    _close_session_quietly(entry)


def _reset(entry: SeriesSession) -> None:
    entry.session.reset_interactions()
    entry.target_buffer.fill(0)
    entry.prompts_seen.clear()
    entry.prompt_order.clear()


# Prompt geometry mirrors the napari-nninteractive plugin (the nnInteractive reference client)
# exactly: the viewer sends unrounded voxel coordinates (napari's data coordinates) and every
# rounding, brush and polygon rule below is napari's, so the same gesture yields the same prompt.


def _viewer_to_model_zyx(point: list[float], entry: SeriesSession) -> list[float]:
    """Viewer [x, y, slice] (continuous) → model [z, y, x] (continuous, flip applied)."""
    x, y, z = (float(v) for v in point[:3])
    if entry.flipped:
        z = entry.target_buffer.shape[0] - 1 - z
    return [z, y, x]


def _bbox_to_half_open_intervals(corners_zyx: np.ndarray) -> list[list[float]]:
    """napari-nninteractive's _bbox_to_half_open_intervals: the session rounds the floats."""
    mins = np.min(corners_zyx, axis=0).astype(float)
    maxs = np.max(corners_zyx, axis=0).astype(float)
    collapsed = mins == maxs
    maxs[collapsed] = maxs[collapsed] + 1.0
    return [[float(mins[i]), float(maxs[i])] for i in range(len(mins))]


def _interpolate_coordinates(old_coord: np.ndarray, new_coord: np.ndarray, brush_size: float) -> np.ndarray:
    """napari.layers.labels._labels_utils.interpolate_coordinates."""
    num_step = round(max(abs(np.array(new_coord) - np.array(old_coord))) / brush_size * 4)
    coords = [np.linspace(old_coord[i], new_coord[i], num=int(num_step + 1)) for i in range(len(new_coord))]
    coords = np.stack(coords).T
    if len(coords) > 1:
        coords = coords[1:]
    return coords


def _sphere_indices(radius: float, scale: tuple[float, ...]) -> np.ndarray:
    """napari.layers.labels._labels_utils.sphere_indices."""
    ndim = len(scale)
    abs_scale = np.abs(scale)
    scale_normalized = np.asarray(abs_scale, dtype=float) / np.min(abs_scale)
    r_normalized = radius / scale_normalized + 0.5
    slices = [slice(-int(np.ceil(r)), int(np.floor(r)) + 1) for r in r_normalized]
    indices = np.mgrid[slices].T.reshape(-1, ndim)
    distances_sq = np.sum((indices * scale_normalized) ** 2, axis=1)
    return indices[distances_sq <= radius**2].astype(int)


def _flat_axis_zyx(points_zyx: np.ndarray, flat_axis_xyz: Any) -> int:
    """The axis not displayed while drawing: the payload's, else the one the stroke does not move along."""
    axis = _coerce_flat_axis(flat_axis_xyz)
    if axis is not None:
        return 2 - axis
    return int(np.argmin(np.ptp(points_zyx, axis=0)))


def _slice_id(points_zyx: np.ndarray, flat: int, shape_zyx: tuple[int, int, int]) -> int:
    # napari: int(np.rint(dims point)), clipped into the volume.
    return int(np.clip(int(np.rint(float(points_zyx[0, flat]))), 0, shape_zyx[flat] - 1))


def _crop_on_plane(
    plane: np.ndarray, flat: int, sid: int, lo: Any, hi: Any
) -> tuple[np.ndarray, list[list[int]]]:
    crop_3d = np.expand_dims(plane[lo[0] : hi[0], lo[1] : hi[1]].astype(np.uint8), axis=flat)
    displayed = [d for d in range(3) if d != flat]
    bbox = [[0, 0], [0, 0], [0, 0]]
    bbox[flat] = [sid, sid + 1]
    bbox[displayed[0]] = [int(lo[0]), int(hi[0])]
    bbox[displayed[1]] = [int(lo[1]), int(hi[1])]
    return crop_3d, bbox


def _prepare_scribble(
    shape_zyx: tuple[int, int, int],
    points_zyx: np.ndarray,
    flat: int,
    brush_size: float,
    spacing_zyx: tuple[float, float, float],
) -> tuple[np.ndarray | None, list[list[int]] | None]:
    """Paint the stroke like a napari Labels brush, then crop it like ScribbleLayer.get_last."""
    sid = _slice_id(points_zyx, flat, shape_zyx)
    displayed = [d for d in range(3) if d != flat]
    plane_shape = np.array([shape_zyx[d] for d in displayed])
    plane = np.zeros(plane_shape, dtype=bool)
    # Ensure circle doesn't have spurious point on edge by keeping radius as ##.5 (napari).
    radius = np.floor(brush_size / 2) + 0.5
    offsets = _sphere_indices(radius, tuple(float(spacing_zyx[d]) for d in displayed))

    def paint(coord: np.ndarray) -> None:
        indices = offsets + np.round(coord[displayed]).astype(int)
        valid = np.all((indices >= 0) & (indices < plane_shape), axis=1)
        plane[indices[valid, 0], indices[valid, 1]] = True

    stroke = points_zyx.astype(float).copy()
    stroke[:, flat] = sid  # napari strokes lie on the displayed slice
    # napari's draw: paint the press position, then interpolate along every mouse move.
    paint(stroke[0])
    for old, new in zip(stroke[:-1], stroke[1:]):
        for coord in _interpolate_coordinates(old, new, brush_size):
            paint(coord)

    ij = np.argwhere(plane)
    if len(ij) == 0:
        return None, None
    return _crop_on_plane(plane, flat, sid, ij.min(axis=0), ij.max(axis=0) + 1)


def _prepare_lasso(
    shape_zyx: tuple[int, int, int],
    points_zyx: np.ndarray,
    flat: int,
) -> tuple[np.ndarray | None, list[list[int]] | None]:
    """LassoLayer.get_last: fill the float polygon with skimage's polygon2mask on a tight crop."""
    if len(points_zyx) < 3:
        return None, None
    sid = _slice_id(points_zyx, flat, shape_zyx)
    polygon_2d = np.delete(points_zyx.astype(float), flat, axis=1)
    slice_shape = np.delete(np.array(shape_zyx), flat)
    lo = np.floor(polygon_2d.min(axis=0)).astype(int)
    hi = np.ceil(polygon_2d.max(axis=0)).astype(int) + 1
    lo = np.clip(lo, 0, slice_shape - 1)
    hi = np.clip(hi, lo + 1, slice_shape)
    mask = polygon2mask((int(hi[0] - lo[0]), int(hi[1] - lo[1])), polygon_2d - lo)
    if not mask.any():
        return None, None
    full = np.zeros(slice_shape, dtype=bool)
    full[lo[0] : hi[0], lo[1] : hi[1]] = mask
    return _crop_on_plane(full, flat, sid, lo, hi)


def _coerce_flat_axis(axis: Any) -> int | None:
    try:
        coerced = int(axis)
    except (TypeError, ValueError):
        return None
    return coerced if coerced in (0, 1, 2) else None


def _union_bbox(a: Any, b: Any) -> Any:
    if a is None:
        return b
    if b is None:
        return a
    return [[min(a[i][0], b[i][0]), max(a[i][1], b[i][1])] for i in range(3)]


def _preferred_brush_size(entry: SeriesSession, flat_zyx: int) -> float:
    # napari sets the scribble brush_size to the session's preferred_scribble_thickness for the
    # axis not displayed (target-buffer order [z, y, x]).
    preferred = getattr(entry.session, "preferred_scribble_thickness", None)
    value: Any = None
    if isinstance(preferred, (list, tuple)) and len(preferred) > flat_zyx:
        value = preferred[flat_zyx]
    elif isinstance(preferred, (int, float)):
        value = preferred
    try:
        return max(1.0, float(value))
    except (TypeError, ValueError):
        return 2.0


def _freehand_points_zyx(prompt: Any, entry: SeriesSession) -> tuple[np.ndarray, int] | None:
    raw_points, flat_axis_xyz = _prompt_points_and_flat_axis(prompt)
    points = []
    for point in raw_points if isinstance(raw_points, list) else []:
        if not isinstance(point, (list, tuple)) or len(point) < 3:
            continue
        try:
            zyx = _viewer_to_model_zyx(point, entry)
        except (TypeError, ValueError):
            continue
        if all(math.isfinite(v) for v in zyx):
            points.append(zyx)
    if not points:
        return None
    points_zyx = np.asarray(points, dtype=float)
    return points_zyx, _flat_axis_zyx(points_zyx, flat_axis_xyz)


def _prompt_points_and_flat_axis(prompt: Any) -> tuple[Any, int | None]:
    if not isinstance(prompt, dict):
        return prompt, None
    return prompt.get("points", []), _coerce_flat_axis(prompt.get("axis"))


# Payload fields per prompt kind, in the order prompts are applied (napari's order).
PROMPT_KINDS = ("points", "boxes", "lassos", "scribbles")


def _send_prompt(entry: SeriesSession, kind: str, prompt: Any, include: bool) -> Any:
    """Add one prompt to the session. Returns the changed-region bbox it reports, or None."""
    session = entry.session
    if kind == "points":
        # Unrounded, like napari's point layer; the session rounds.
        return session.add_point_interaction(_viewer_to_model_zyx(prompt, entry), include_interaction=include)
    if kind == "boxes":
        corners = np.asarray([_viewer_to_model_zyx(corner, entry) for corner in prompt], dtype=float)
        return session.add_bbox_interaction(_bbox_to_half_open_intervals(corners), include_interaction=include)

    parsed = _freehand_points_zyx(prompt, entry)
    if parsed is None:
        return None
    shape = entry.target_buffer.shape
    if kind == "lassos":
        mask, bbox = _prepare_lasso(shape, *parsed)
        add = session.add_lasso_interaction
    else:
        points_zyx, flat = parsed
        mask, bbox = _prepare_scribble(shape, points_zyx, flat, _preferred_brush_size(entry, flat), entry.spacing_zyx)
        add = session.add_scribble_interaction
    if mask is None:
        return None
    return add(mask, include_interaction=include, interaction_bbox=bbox)


def _apply_prompts(entry: SeriesSession, data: dict[str, Any]) -> tuple[dict[str, int], Any]:
    """Apply the prompts not seen before (deduplicated by content). Returns (counts per payload
    field, changed_bbox) — the union of the changed-region bboxes the session reports per
    interaction ([[z0,z1],[y0,y1],[x0,x1]] in raw buffer coords), or None if nothing visibly changed."""
    counts: dict[str, int] = {}
    changed: Any = None
    for kind in PROMPT_KINDS:
        for sign, include in (("pos", True), ("neg", False)):
            field = f"{sign}_{kind}"
            counts[field] = 0
            for prompt in _as_list(data.get(field)):
                if kind == "boxes" and not (isinstance(prompt, list) and len(prompt) == 2):
                    continue
                key = _prompt_key(field, prompt)
                if key in entry.prompts_seen:
                    continue
                changed = _union_bbox(changed, _send_prompt(entry, kind, prompt, include))
                entry.prompts_seen.add(key)
                entry.prompt_order.append(key)
                counts[field] += 1
    return counts, changed


Crop = tuple[bytes, list[int], list[int], list[int]]


def _empty_crop(target_buffer: np.ndarray) -> Crop:
    return b"", [0, 0, 0], [int(x) for x in target_buffer.shape], [0, 0, 0]


def _crop_target_bbox(target_buffer: np.ndarray, bbox: Any) -> Crop:
    """Slice a region ([[z0,z1],[y0,y1],[x0,x1]]) out of the buffer.
    Returns (bytes, offset [z0,y0,x0], full shape, crop shape)."""
    full_shape = [int(x) for x in target_buffer.shape]
    (z0, z1), (y0, y1), (x0, x1) = (
        (max(0, int(lo)), min(size, int(hi))) for (lo, hi), size in zip(bbox, full_shape)
    )
    if z1 <= z0 or y1 <= y0 or x1 <= x0:
        return _empty_crop(target_buffer)
    crop = np.ascontiguousarray(target_buffer[z0:z1, y0:y1, x0:x1])
    return crop.tobytes(order="C"), [z0, y0, x0], full_shape, [z1 - z0, y1 - y0, x1 - x0]


def _crop_target(target_buffer: np.ndarray) -> Crop:
    """The buffer's whole foreground, cropped to its bounding box."""
    bbox = []
    for axes in ((1, 2), (0, 2), (0, 1)):
        indices = np.flatnonzero(np.any(target_buffer, axis=axes))
        if not len(indices):
            return _empty_crop(target_buffer)
        bbox.append([int(indices[0]), int(indices[-1]) + 1])
    return _crop_target_bbox(target_buffer, bbox)


def _multipart(meta: dict[str, Any], seg: bytes) -> Response:
    boundary = f"nninteractive-{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="meta"\r\n'
        "Content-Type: application/json\r\n\r\n"
    ).encode("utf-8")
    body += json.dumps(meta, separators=(",", ":")).encode("utf-8")
    body += (
        f"\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="seg"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    body += seg
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")
    return Response(body, media_type=f'multipart/form-data; boundary="{boundary}"')


def _response(
    entry: SeriesSession,
    crop: Crop,
    start: float,
    prompt_info: str,
    extra: dict[str, Any] | None = None,
) -> Response:
    seg, offset, full_shape, crop_shape = crop
    meta = {
        "flipped": str(entry.flipped).lower(),
        "nninter_elapsed": f"{time.time() - start:.3f}",
        "prompt_info": prompt_info,
        "pred_offset": json.dumps(offset),
        "pred_full_shape": json.dumps(full_shape),
        "pred_crop_shape": json.dumps(crop_shape),
    }
    if extra:
        meta.update(
            {
                key: str(value).lower() if isinstance(value, bool) else str(value)
                for key, value in extra.items()
            }
        )
    return _multipart(meta, seg)


def _gunzip_limited(data: bytes, limit: int) -> bytes:
    """Decompress at most `limit` bytes, so a small upload cannot expand without bound."""
    try:
        decompressor = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
        out = decompressor.decompress(data, limit + 1)
    except zlib.error as e:
        raise HTTPException(400, "Mask is not valid gzip") from e
    if len(out) > limit or decompressor.unconsumed_tail:
        raise HTTPException(400, "Mask is larger than the target volume")
    return out


def _forward_auth_headers(request: Request) -> dict[str, str]:
    headers = {}
    authorization = request.headers.get("authorization")
    forwarded_token = request.headers.get("x-forwarded-access-token")
    if authorization:
        headers["Authorization"] = authorization
    if forwarded_token:
        headers["x-forwarded-access-token"] = forwarded_token
    # Set by traefik's auth-check for /project/<id>/ URLs; dicom-web-filter scopes reads to it.
    project = request.headers.get("project")
    if project:
        headers["Project"] = project
    return headers


def _run_inference_request(entry: SeriesSession, mode: Any, data: dict[str, Any], start: float) -> Response:
    if mode == "init":
        return _response(entry, _empty_crop(entry.target_buffer), start, "initialized")

    if mode == "reset":
        _reset(entry)
        return _response(entry, _empty_crop(entry.target_buffer), start, "reset")

    if mode == "undo":
        ran = entry.session.undo()
        if ran and entry.prompt_order:
            entry.prompts_seen.discard(entry.prompt_order.pop())
        # undo() only returns a bool; the changed-region bbox of the restore is exposed via the
        # remote client's _last_paste_bbox (private, but it mirrors the server response verbatim).
        undo_bbox = getattr(entry.session, "_last_paste_bbox", None) if ran else None
        # Nothing undone / no visible change → empty delta (the client stops at undone=false).
        crop = _crop_target_bbox(entry.target_buffer, undo_bbox) if undo_bbox is not None else _empty_crop(entry.target_buffer)
        return _response(entry, crop, start, "undo", {"undone": ran, "pred_scope": "delta"})

    if mode == "set_mask":
        mask_bytes = data.get("mask_bytes")
        if not isinstance(mask_bytes, (bytes, bytearray)):
            raise HTTPException(400, "Missing required mask file for set_mask")
        # The client gzips the (very sparse) full-volume mask; raw uploads remain valid.
        expected_size = int(np.prod(entry.target_buffer.shape))
        if bytes(mask_bytes[:2]) == b"\x1f\x8b":
            mask_bytes = _gunzip_limited(bytes(mask_bytes), expected_size)
        if len(mask_bytes) != expected_size:
            raise HTTPException(
                400,
                f"Mask byte length {len(mask_bytes)} does not match target volume size {expected_size}",
            )
        mask = np.frombuffer(mask_bytes, dtype=np.uint8).reshape(entry.target_buffer.shape)
        if entry.flipped:
            mask = mask[::-1]
        seg01 = np.ascontiguousarray((mask > 0).astype(np.uint8))
        # Feed the mask into the model's prev_seg channel AND the target buffer (resets interactions,
        # commits an undo snapshot). Poking only the output buffer leaves the model's prior EMPTY, so
        # the next prompt predicts from nothing and wipes the object.
        entry.session.add_initial_seg_interaction(seg01, run_prediction=False)
        entry.prompts_seen.clear()
        entry.prompt_order.clear()
        return _response(entry, _crop_target(entry.target_buffer), start, "manual correction", {"pred_scope": "full"})

    if mode is not True:
        raise HTTPException(400, "Only nnInteractive requests are supported")

    reset_first = _jsonish(data.get("nninter_reset_first"), False)
    if reset_first:
        _reset(entry)

    counts, changed_bbox = _apply_prompts(entry, data)
    if reset_first:
        # Replay from scratch — the client must rebuild the whole object.
        crop, scope = _crop_target(entry.target_buffer), "full"
    elif changed_bbox is not None:
        # Ship only the changed region the session reported.
        crop, scope = _crop_target_bbox(entry.target_buffer, changed_bbox), "delta"
    else:
        crop, scope = _empty_crop(entry.target_buffer), "delta"
    prompt_info = ", ".join(f"{k}={v}" for k, v in counts.items() if v) or "no new prompts"
    return _response(entry, crop, start, prompt_info, {"pred_scope": scope})


def _infer_segmentation_sync(
    principal: str,
    study_uid: str,
    series_uid: str,
    client_session_id: str,
    data: dict[str, Any],
    dicomweb_headers: dict[str, str] | None,
    mode: Any,
    start: float,
) -> Response:
    # Only an explicit "init" request may create a session. Every other mode answers 409 when the
    # session is gone, so the client re-initializes and re-uploads its mask instead of prompting
    # an empty session.
    if mode == "init":
        entry = _get_series_session(
            principal,
            study_uid,
            series_uid,
            client_session_id,
            dicomweb_headers,
            data.get("firstSOPInstanceUID"),
            data.get("volumeShape"),
        )
    else:
        entry = _touch_session(_session_key(principal, study_uid, series_uid, client_session_id))
        if entry is None:
            raise HTTPException(409, "no active nnInteractive session; initialize first")

    try:
        with entry.lock:
            return _run_inference_request(entry, mode, data, start)

    except SessionExpiredError as e:
        # Never recreate and replay here: a fresh session has lost the object's mask, so replaying
        # the prompt would predict from nothing. The client re-initializes and re-uploads the mask.
        logger.info("nnInteractive session expired for %s", series_uid)
        _close_entry(entry)
        raise HTTPException(409, "nnInteractive session expired; initialize again") from e


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    with sessions_lock:
        cached_sessions = len(sessions)
    return {"ok": True, "nninteractive_server": NNINTERACTIVE_SERVER_URL, "cached_sessions": cached_sessions}


@app.get("/infer/availability")
def availability() -> dict[str, Any]:
    try:
        response = requests.get(NNINTERACTIVE_SERVER_URL, timeout=2)
        server_available = response.status_code < 500
        return {
            "available": server_available,
            "proxy": True,
            "nninteractive_server": NNINTERACTIVE_SERVER_URL,
            "server_status": response.status_code,
        }
    except Exception as e:
        return {
            "available": False,
            "proxy": True,
            "nninteractive_server": NNINTERACTIVE_SERVER_URL,
            "error": str(e),
        }


@app.get("/infer/session")
def session_status(
    request: Request,
    image: str | None = None,
    studyInstanceUID: str | None = None,
    clientSessionID: str | None = None,
) -> dict[str, Any]:
    """Non-creating liveness probe used by the OHIF UI to gate prompts.

    Returns ``{"active": False}`` when no session exists for the series or the
    upstream lease has expired (the dead entry is dropped); otherwise
    ``{"active": True, "remaining_seconds": <idle seconds left>}``. Doubles as the
    browser heartbeat: it stamps ``last_browser_seen`` so the proxy knows the tab
    is still around.
    """
    if not image or not studyInstanceUID:
        raise HTTPException(400, "Missing required query parameters: image, studyInstanceUID")
    with sessions_lock:
        entry = sessions.get(
            _session_key(_principal(request), studyInstanceUID, image, _client_session_id(clientSessionID))
        )
    if entry is None:
        return {"active": False}
    entry.last_browser_seen = time.time()
    try:
        with entry.lock:
            status_info = entry.session.lease_status()
    except SessionExpiredError:
        _close_entry(entry)
        return {"active": False}
    except Exception:
        # Treat an unreachable upstream as "unknown but still ours"; don't drop the
        # entry on a transient blip — the next real request will surface a hard error.
        logger.warning("lease_status() failed for %s", image, exc_info=True)
        return {"active": True}
    return {"active": True, "remaining_seconds": status_info.get("remaining_seconds")}


@app.post("/infer/close")
async def close_session(request: Request) -> dict[str, Any]:
    """Release the nnInteractive lease when the user leaves the OHIF page.

    Accepts the series/study via query params or a form body (the browser sends a keepalive
    fetch with a form during unload). Idempotent.
    """
    series_uid = request.query_params.get("image")
    study_uid = request.query_params.get("studyInstanceUID")
    client_session_id = request.query_params.get("clientSessionID")
    if not series_uid or not study_uid:
        try:
            form = await request.form()
            series_uid = series_uid or form.get("image")
            study_uid = study_uid or form.get("studyInstanceUID")
            client_session_id = client_session_id or form.get("clientSessionID")
        except Exception:
            pass
    if not series_uid or not study_uid:
        raise HTTPException(400, "Missing required parameters: image, studyInstanceUID")
    with sessions_lock:
        entry = sessions.get(
            _session_key(
                _principal(request), str(study_uid), str(series_uid), _client_session_id(client_session_id)
            )
        )
    if entry is None:
        return {"closed": False}
    await anyio.to_thread.run_sync(_close_entry, entry)
    return {"closed": True}


@app.post("/infer/segmentation")
async def infer_segmentation(request: Request) -> Response:
    start = time.time()
    series_uid = request.query_params.get("image")
    if not series_uid:
        raise HTTPException(400, "Missing required query parameter: image")

    form = await request.form()
    data = {}
    if "params" in form:
        params = _jsonish(form.get("params"), {})
        if not isinstance(params, dict):
            raise HTTPException(400, "Form field 'params' must contain a JSON object")
        data.update(params)
    data.update({key: form.get(key) for key in form.keys() if key != "params"})
    mask_file = form.get("mask")
    if hasattr(mask_file, "read"):
        if (getattr(mask_file, "size", None) or 0) > MAX_MASK_UPLOAD_BYTES:
            raise HTTPException(413, "Mask upload is too large")
        data["mask_bytes"] = await mask_file.read()
    study_uid = str(data.get("studyInstanceUID") or "")
    if not study_uid:
        raise HTTPException(400, "Missing required form field: studyInstanceUID")
    client_session_id = _client_session_id(data.get("clientSessionID"))

    mode = _jsonish(data.get("nninter"), False)

    try:
        return await anyio.to_thread.run_sync(
            _infer_segmentation_sync,
            _principal(request),
            study_uid,
            series_uid,
            client_session_id,
            data,
            _forward_auth_headers(request),
            mode,
            start,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("nnInteractive proxy request failed")
        raise HTTPException(500, "nnInteractive proxy request failed") from e
