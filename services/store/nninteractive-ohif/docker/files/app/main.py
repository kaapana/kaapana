import json
import logging
import math
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from email.parser import BytesParser
from email.policy import default
from typing import Any

import numpy as np
import pydicom
import requests
import SimpleITK as sitk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from nnInteractive.inference.remote import (
    ServerAtCapacityError,
    SessionExpiredError,
    nnInteractiveRemoteInferenceSession,
)
from scipy.ndimage import binary_dilation, binary_fill_holes

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
MAX_CACHED_SESSIONS = int(os.environ.get("MAX_CACHED_SESSIONS", "1"))
REQUEST_TIMEOUT = float(os.environ.get("DICOMWEB_REQUEST_TIMEOUT", "120"))

app = FastAPI(title="OHIF nnInteractive proxy", version="0.1.0")


@dataclass
class SeriesSession:
    key: str
    study_uid: str
    series_uid: str
    session: nnInteractiveRemoteInferenceSession
    target_buffer: np.ndarray
    flipped: bool
    prompts_seen: set[str] = field(default_factory=set)
    prompt_order: list[str] = field(default_factory=list)
    last_used: float = field(default_factory=time.time)
    last_browser_seen: float = field(default_factory=time.time)


sessions: dict[str, SeriesSession] = {}


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


def _auth() -> tuple[str, str] | None:
    username = os.environ.get("DICOMWEB_USERNAME")
    password = os.environ.get("DICOMWEB_PASSWORD")
    return (username, password) if username and password else None


def _dicomweb_get(path: str, headers: dict[str, str] | None = None) -> requests.Response:
    url = f"{DICOMWEB_ROOT}/{path.lstrip('/')}"
    request_headers = {
        "Accept": 'multipart/related; type="application/dicom"; transfer-syntax=*',
    }
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


def _load_image(study_uid: str, series_uid: str, headers: dict[str, str] | None) -> tuple[np.ndarray, bool]:
    with tempfile.TemporaryDirectory(prefix="nninteractive-proxy-") as tempdir:
        _fetch_series_to_tempdir(study_uid, series_uid, tempdir, headers)
        reader = sitk.ImageSeriesReader()
        series_ids = reader.GetGDCMSeriesIDs(tempdir)
        if not series_ids:
            raise HTTPException(502, "SimpleITK could not identify a DICOM series")
        files = list(reader.GetGDCMSeriesFileNames(tempdir, series_ids[0]))
        reader.SetFileNames(files)
        image = reader.Execute()

        flipped = False
        if len(files) >= 2:
            try:
                first = pydicom.dcmread(files[0], stop_before_pixels=True, force=True)
                second = pydicom.dcmread(files[1], stop_before_pixels=True, force=True)
                flipped = int(first.get("InstanceNumber", 0)) > int(second.get("InstanceNumber", 0))
            except Exception:
                logger.warning("Could not determine slice flip from InstanceNumber", exc_info=True)

        volume = sitk.GetArrayFromImage(image).astype(np.float32, copy=False)
        return np.ascontiguousarray(volume[None]), flipped


def _new_remote_session(image_4d: np.ndarray) -> tuple[nnInteractiveRemoteInferenceSession, np.ndarray]:
    session = nnInteractiveRemoteInferenceSession(
        server_url=NNINTERACTIVE_SERVER_URL,
        api_key=NNINTERACTIVE_API_KEY,
        connect_timeout=10,
        read_timeout=float(os.environ.get("NNINTERACTIVE_READ_TIMEOUT", "120")),
        set_image_read_timeout=float(os.environ.get("NNINTERACTIVE_SET_IMAGE_TIMEOUT", "900")),
        write_timeout=float(os.environ.get("NNINTERACTIVE_WRITE_TIMEOUT", "300")),
    )
    session.set_image(image_4d)
    target_buffer = np.zeros(image_4d.shape[1:], dtype=np.uint8)
    session.set_target_buffer(target_buffer)
    return session, target_buffer


def _evict_if_needed() -> None:
    while len(sessions) >= MAX_CACHED_SESSIONS:
        oldest_key = min(sessions, key=lambda k: sessions[k].last_used)
        old = sessions.pop(oldest_key)
        try:
            old.session.close()
        except Exception:
            logger.warning("Failed to close old nnInteractive session", exc_info=True)


def _get_series_session(
    study_uid: str,
    series_uid: str,
    dicomweb_headers: dict[str, str] | None,
) -> SeriesSession:
    key = f"{study_uid}|{series_uid}"
    existing = sessions.get(key)
    if existing is not None:
        existing.last_used = time.time()
        return existing

    _evict_if_needed()
    try:
        load_start = time.time()
        image_4d, flipped = _load_image(study_uid, series_uid, dicomweb_headers)
        session, target_buffer = _new_remote_session(image_4d)
        logger.info(
            "Initialized nnInteractive session for %s in %.3fs; image shape=%s flipped=%s",
            series_uid,
            time.time() - load_start,
            image_4d.shape,
            flipped,
        )
    except ServerAtCapacityError as e:
        raise HTTPException(503, "nnInteractive server is at capacity") from e
    except requests.HTTPError as e:
        raise HTTPException(502, f"DICOMweb request failed: {e}") from e
    except Exception as e:
        raise HTTPException(502, f"Could not initialize nnInteractive session: {e}") from e

    entry = SeriesSession(key, study_uid, series_uid, session, target_buffer, flipped)
    sessions[key] = entry
    return entry


def _close_entry(entry: SeriesSession) -> None:
    sessions.pop(entry.key, None)
    try:
        entry.session.close()
    except Exception:
        logger.warning("Failed to close nnInteractive session", exc_info=True)


def _reset(entry: SeriesSession) -> None:
    entry.session.reset_interactions()
    entry.target_buffer.fill(0)
    entry.prompts_seen.clear()
    entry.prompt_order.clear()


def _flip_z_if_needed(point: list[float], entry: SeriesSession) -> list[float]:
    point = list(point)
    if entry.flipped:
        point[2] = entry.target_buffer.shape[0] - 1 - point[2]
    return point


def _viewer_point_to_model(point: list[float], entry: SeriesSession) -> list[int]:
    return [int(round(v)) for v in _flip_z_if_needed(point, entry)[::-1]]


def clean_and_densify_polyline(polyline: list, max_segment_length: int = 1) -> list[list[int]]:
    if not polyline or len(polyline) < 2:
        return []
    cleaned = []
    for i in range(len(polyline)):
        x1, y1, z = polyline[i]
        x2, y2, _ = polyline[(i + 1) % len(polyline)]
        if x1 == x2 and y1 == y2:
            continue
        if not cleaned or cleaned[-1][0] != x1 or cleaned[-1][1] != y1:
            cleaned.append([x1, y1, z])
        dx, dy = x2 - x1, y2 - y1
        distance = math.hypot(dx, dy)
        if distance > max_segment_length:
            steps = math.floor(distance)
            for j in range(1, steps):
                t = j / steps
                px, py = round(x1 + dx * t), round(y1 + dy * t)
                if cleaned[-1][0] != px or cleaned[-1][1] != py:
                    cleaned.append([px, py, z])
    if cleaned and (cleaned[0][0] != cleaned[-1][0] or cleaned[0][1] != cleaned[-1][1]):
        cleaned.append([cleaned[0][0], cleaned[0][1], cleaned[-1][2]])
    return cleaned


def scribble_constant_axis(points: np.ndarray) -> int | None:
    if points.size == 0:
        return None
    for axis in (0, 1, 2):
        if np.unique(points[:, axis]).size == 1:
            return axis
    return None


def _rasterize_polygon_2d(rows: np.ndarray, cols: np.ndarray, height: int, width: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=bool)
    for i in range(len(rows)):
        r0, c0 = int(rows[i]), int(cols[i])
        r1, c1 = int(rows[(i + 1) % len(rows)]), int(cols[(i + 1) % len(cols)])
        steps = max(abs(r1 - r0), abs(c1 - c0)) + 1
        rs = np.round(np.linspace(r0, r1, steps)).astype(int)
        cs = np.round(np.linspace(c0, c1, steps)).astype(int)
        valid = (rs >= 0) & (rs < height) & (cs >= 0) & (cs < width)
        mask[rs[valid], cs[valid]] = True
    return binary_fill_holes(mask)


def _bbox_from_mask(mask: np.ndarray) -> list[list[int]] | None:
    coords = np.nonzero(mask)
    if coords[0].size == 0:
        return None
    return [[int(axis.min()), int(axis.max()) + 1] for axis in coords]


def _prepare_scribble(volume_shape_zyx: tuple[int, int, int], points_xyz: np.ndarray) -> tuple[np.ndarray | None, list[list[int]] | None]:
    flat_axis = scribble_constant_axis(points_xyz)
    z_size, y_size, x_size = volume_shape_zyx
    x_arr, y_arr, z_arr = points_xyz[:, 0], points_xyz[:, 1], points_xyz[:, 2]
    kernel = np.ones((2, 2), dtype=bool)

    if flat_axis == 2:
        z_val = int(z_arr[0])
        mask = np.zeros((y_size, x_size), dtype=bool)
        valid = (x_arr >= 0) & (x_arr < x_size) & (y_arr >= 0) & (y_arr < y_size)
        mask[y_arr[valid], x_arr[valid]] = True
        dil = binary_dilation(mask, structure=kernel)
        bbox_2d = _bbox_from_mask(dil)
        if bbox_2d is None:
            return None, None
        (y0, y1), (x0, x1) = bbox_2d
        return dil[y0:y1, x0:x1].astype(np.uint8)[None], [[z_val, z_val + 1], [y0, y1], [x0, x1]]

    if flat_axis == 1:
        y_val = int(y_arr[0])
        mask = np.zeros((z_size, x_size), dtype=bool)
        valid = (x_arr >= 0) & (x_arr < x_size) & (z_arr >= 0) & (z_arr < z_size)
        mask[z_arr[valid], x_arr[valid]] = True
        dil = binary_dilation(mask, structure=kernel)
        bbox_2d = _bbox_from_mask(dil)
        if bbox_2d is None:
            return None, None
        (z0, z1), (x0, x1) = bbox_2d
        return dil[z0:z1, x0:x1].astype(np.uint8)[:, None, :], [[z0, z1], [y_val, y_val + 1], [x0, x1]]

    if flat_axis == 0:
        x_val = int(x_arr[0])
        mask = np.zeros((z_size, y_size), dtype=bool)
        valid = (y_arr >= 0) & (y_arr < y_size) & (z_arr >= 0) & (z_arr < z_size)
        mask[z_arr[valid], y_arr[valid]] = True
        dil = binary_dilation(mask, structure=kernel)
        bbox_2d = _bbox_from_mask(dil)
        if bbox_2d is None:
            return None, None
        (z0, z1), (y0, y1) = bbox_2d
        return dil[z0:z1, y0:y1].astype(np.uint8)[:, :, None], [[z0, z1], [y0, y1], [x_val, x_val + 1]]

    point_mask = np.zeros(volume_shape_zyx, dtype=bool)
    valid = (
        (x_arr >= 0) & (x_arr < x_size)
        & (y_arr >= 0) & (y_arr < y_size)
        & (z_arr >= 0) & (z_arr < z_size)
    )
    point_mask[z_arr[valid], y_arr[valid], x_arr[valid]] = True
    return binary_dilation(point_mask, structure=np.ones((2, 2, 2), dtype=bool)).astype(np.uint8), None


def _prepare_lasso(volume_shape_zyx: tuple[int, int, int], points_xyz: np.ndarray) -> tuple[np.ndarray | None, list[list[int]] | None]:
    flat_axis = scribble_constant_axis(points_xyz)
    z_size, y_size, x_size = volume_shape_zyx
    x_arr, y_arr, z_arr = points_xyz[:, 0], points_xyz[:, 1], points_xyz[:, 2]
    if flat_axis == 2:
        z_val = int(z_arr[0])
        filled = _rasterize_polygon_2d(y_arr, x_arr, y_size, x_size)
        bbox_2d = _bbox_from_mask(filled)
        if bbox_2d is None:
            return None, None
        (y0, y1), (x0, x1) = bbox_2d
        return filled[y0:y1, x0:x1].astype(np.uint8)[None], [[z_val, z_val + 1], [y0, y1], [x0, x1]]
    if flat_axis == 1:
        y_val = int(y_arr[0])
        filled = _rasterize_polygon_2d(z_arr, x_arr, z_size, x_size)
        bbox_2d = _bbox_from_mask(filled)
        if bbox_2d is None:
            return None, None
        (z0, z1), (x0, x1) = bbox_2d
        return filled[z0:z1, x0:x1].astype(np.uint8)[:, None, :], [[z0, z1], [y_val, y_val + 1], [x0, x1]]
    if flat_axis == 0:
        x_val = int(x_arr[0])
        filled = _rasterize_polygon_2d(z_arr, y_arr, z_size, y_size)
        bbox_2d = _bbox_from_mask(filled)
        if bbox_2d is None:
            return None, None
        (z0, z1), (y0, y1) = bbox_2d
        return filled[z0:z1, y0:y1].astype(np.uint8)[:, :, None], [[z0, z1], [y0, y1], [x_val, x_val + 1]]
    return None, None


def _add_prompt(entry: SeriesSession, kind: str, prompt: Any, callback) -> bool:
    key = _prompt_key(kind, prompt)
    if key in entry.prompts_seen:
        return False
    callback()
    entry.prompts_seen.add(key)
    entry.prompt_order.append(key)
    return True


def _apply_prompts(entry: SeriesSession, data: dict[str, Any]) -> dict[str, int]:
    counts = {
        "pos_points": 0,
        "neg_points": 0,
        "pos_boxes": 0,
        "neg_boxes": 0,
        "pos_lassos": 0,
        "neg_lassos": 0,
        "pos_scribbles": 0,
        "neg_scribbles": 0,
    }
    shape = tuple(int(x) for x in entry.target_buffer.shape)

    for kind, include in (("pos_points", True), ("neg_points", False)):
        for point in _as_list(data.get(kind)):
            def cb(point=point, include=include):
                entry.session.add_point_interaction(_viewer_point_to_model(point, entry), include_interaction=include)
            if _add_prompt(entry, kind, point, cb):
                counts[kind] += 1

    for kind, include in (("pos_boxes", True), ("neg_boxes", False)):
        for box in _as_list(data.get(kind)):
            if not isinstance(box, list) or len(box) != 2:
                continue
            def cb(box=box, include=include):
                p0 = _viewer_point_to_model(box[0], entry)
                p1 = _viewer_point_to_model(box[1], entry)
                bbox = [[min(p0[i], p1[i]), max(p0[i], p1[i]) + 1] for i in range(3)]
                entry.session.add_bbox_interaction(bbox, include_interaction=include)
            if _add_prompt(entry, kind, box, cb):
                counts[kind] += 1

    for kind, include in (("pos_lassos", True), ("neg_lassos", False)):
        for lasso in _as_list(data.get(kind)):
            def cb(lasso=lasso, include=include):
                cleaned = clean_and_densify_polyline(lasso)
                points = np.round(np.asarray(cleaned)).astype(int)
                if points.size == 0:
                    return
                if entry.flipped:
                    points[:, 2] = entry.target_buffer.shape[0] - 1 - points[:, 2]
                mask, bbox = _prepare_lasso(shape, points)
                if mask is not None:
                    entry.session.add_lasso_interaction(mask, include_interaction=include, interaction_bbox=bbox)
            if _add_prompt(entry, kind, lasso, cb):
                counts[kind] += 1

    for kind, include in (("pos_scribbles", True), ("neg_scribbles", False)):
        for scribble in _as_list(data.get(kind)):
            def cb(scribble=scribble, include=include):
                cleaned = clean_and_densify_polyline(scribble)
                points = np.round(np.asarray(cleaned)).astype(int)
                if points.size == 0:
                    return
                if entry.flipped:
                    points[:, 2] = entry.target_buffer.shape[0] - 1 - points[:, 2]
                mask, bbox = _prepare_scribble(shape, points)
                if mask is not None:
                    entry.session.add_scribble_interaction(mask, include_interaction=include, interaction_bbox=bbox)
            if _add_prompt(entry, kind, scribble, cb):
                counts[kind] += 1

    return counts


def _crop_target(target_buffer: np.ndarray) -> tuple[bytes, list[int], list[int], list[int]]:
    full_shape = [int(x) for x in target_buffer.shape]
    z_has = np.any(target_buffer, axis=(1, 2))
    if not z_has.any():
        return b"", [0, 0, 0], full_shape, [0, 0, 0]
    y_has = np.any(target_buffer, axis=(0, 2))
    x_has = np.any(target_buffer, axis=(0, 1))
    z_idx = np.flatnonzero(z_has)
    y_idx = np.flatnonzero(y_has)
    x_idx = np.flatnonzero(x_has)
    z0, z1 = int(z_idx[0]), int(z_idx[-1]) + 1
    y0, y1 = int(y_idx[0]), int(y_idx[-1]) + 1
    x0, x1 = int(x_idx[0]), int(x_idx[-1]) + 1
    crop = np.ascontiguousarray(target_buffer[z0:z1, y0:y1, x0:x1])
    return crop.tobytes(order="C"), [z0, y0, x0], full_shape, [z1 - z0, y1 - y0, x1 - x0]


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


def _meta(
    entry: SeriesSession,
    seg: bytes,
    offset: list[int],
    full_shape: list[int],
    crop_shape: list[int],
    start: float,
    prompt_info: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, str]:
    now = time.time()
    meta = {
        "flipped": str(entry.flipped).lower(),
        "nninter_elapsed": f"{now - start:.3f}",
        "nninter_core_elapsed": f"{now - start:.3f}",
        "server_request_ts": f"{start:.6f}",
        "server_begin_ts": f"{start:.6f}",
        "server_end_ts": f"{now:.6f}",
        "server_load_elapsed": "0.000",
        "server_img_convert_elapsed": "0.000",
        "server_prompt_prep_elapsed": "0.000",
        "server_result_elapsed": "0.000",
        "nninter_first_interaction_ts": f"{start:.6f}",
        "prompt_info": prompt_info,
        "label_name": "nnInteractive",
        "pred_offset": json.dumps(offset),
        "pred_full_shape": json.dumps(full_shape),
        "pred_crop_shape": json.dumps(crop_shape),
        "seg_bytes": str(len(seg)),
    }
    if extra:
        meta.update(
            {
                key: str(value).lower() if isinstance(value, bool) else str(value)
                for key, value in extra.items()
            }
        )
    return meta


def _forward_auth_headers(request: Request) -> dict[str, str]:
    headers = {}
    authorization = request.headers.get("authorization")
    forwarded_token = request.headers.get("x-forwarded-access-token")
    if authorization:
        headers["Authorization"] = authorization
    if forwarded_token:
        headers["x-forwarded-access-token"] = forwarded_token
    return headers


def _run_inference_request(entry: SeriesSession, mode: Any, data: dict[str, Any], start: float) -> Response:
    if mode == "init":
        seg, offset, full_shape, crop_shape = _crop_target(entry.target_buffer)
        return _multipart(_meta(entry, b"", [0, 0, 0], full_shape, [0, 0, 0], start, "initialized"), b"")

    if mode == "reset":
        _reset(entry)
        seg, offset, full_shape, crop_shape = _crop_target(entry.target_buffer)
        return _multipart(_meta(entry, b"", offset, full_shape, crop_shape, start, "reset"), b"")

    if mode == "undo":
        ran = entry.session.undo()
        if ran and entry.prompt_order:
            entry.prompts_seen.discard(entry.prompt_order.pop())
        seg, offset, full_shape, crop_shape = _crop_target(entry.target_buffer)
        return _multipart(_meta(entry, seg, offset, full_shape, crop_shape, start, "undo", {"undone": ran}), seg)

    if mode == "set_mask":
        mask_bytes = data.get("mask_bytes")
        if not isinstance(mask_bytes, (bytes, bytearray)):
            raise HTTPException(400, "Missing required mask file for set_mask")
        expected_size = int(np.prod(entry.target_buffer.shape))
        if len(mask_bytes) != expected_size:
            raise HTTPException(
                400,
                f"Mask byte length {len(mask_bytes)} does not match target volume size {expected_size}",
            )
        mask = np.frombuffer(mask_bytes, dtype=np.uint8).reshape(entry.target_buffer.shape)
        if entry.flipped:
            mask = mask[::-1]
        entry.target_buffer[...] = (mask > 0).astype(np.uint8)
        entry.session.set_target_buffer(entry.target_buffer)
        entry.prompts_seen.clear()
        entry.prompt_order.clear()
        seg, offset, full_shape, crop_shape = _crop_target(entry.target_buffer)
        return _multipart(_meta(entry, seg, offset, full_shape, crop_shape, start, "manual correction"), seg)

    if mode is not True and str(mode).lower() != "true":
        raise HTTPException(400, "Only nnInteractive requests are supported")

    if _jsonish(data.get("nninter_reset_first"), False):
        _reset(entry)

    counts = _apply_prompts(entry, data)
    seg, offset, full_shape, crop_shape = _crop_target(entry.target_buffer)
    prompt_info = ", ".join(f"{k}={v}" for k, v in counts.items() if v) or "no new prompts"
    return _multipart(_meta(entry, seg, offset, full_shape, crop_shape, start, prompt_info), seg)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "nninteractive_server": NNINTERACTIVE_SERVER_URL, "cached_sessions": len(sessions)}


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
def session_status(image: str | None = None, studyInstanceUID: str | None = None) -> dict[str, Any]:
    """Non-creating liveness probe used by the OHIF UI to gate prompts.

    Returns ``{"active": False}`` when no session exists for the series or the
    upstream lease has expired (the dead entry is dropped); otherwise
    ``{"active": True, "remaining_seconds": <idle seconds left>}``. Doubles as the
    browser heartbeat: it stamps ``last_browser_seen`` so the proxy knows the tab
    is still around.
    """
    if not image or not studyInstanceUID:
        raise HTTPException(400, "Missing required query parameters: image, studyInstanceUID")
    entry = sessions.get(f"{studyInstanceUID}|{image}")
    if entry is None:
        return {"active": False}
    entry.last_browser_seen = time.time()
    try:
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

    Accepts the series/study via query params or a ``navigator.sendBeacon`` form
    body (beacons can't set query strings reliably during unload). Idempotent.
    """
    series_uid = request.query_params.get("image")
    study_uid = request.query_params.get("studyInstanceUID")
    if not series_uid or not study_uid:
        try:
            form = await request.form()
            series_uid = series_uid or form.get("image")
            study_uid = study_uid or form.get("studyInstanceUID")
        except Exception:
            pass
    if not series_uid or not study_uid:
        raise HTTPException(400, "Missing required parameters: image, studyInstanceUID")
    entry = sessions.get(f"{study_uid}|{series_uid}")
    if entry is None:
        return {"closed": False}
    _close_entry(entry)
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
        data["mask_bytes"] = await mask_file.read()
    study_uid = str(data.get("studyInstanceUID") or "")
    if not study_uid:
        raise HTTPException(400, "Missing required form field: studyInstanceUID")

    mode = _jsonish(data.get("nninter"), False)
    if mode in {"medGemma", "gemini", "openai", "claude", "kimi", "qwen", "gemma", "vllm"}:
        raise HTTPException(501, f"Text/VLM mode '{mode}' is not implemented by this nnInteractive proxy")

    dicomweb_headers = _forward_auth_headers(request)
    # Only an explicit "init" request may create a session. Every other mode
    # (inference / undo / reset) requires the user to have initialized first, so
    # the OHIF UI can gate prompts on a live session instead of silently spinning
    # one up on the first click.
    if mode == "init":
        entry = _get_series_session(study_uid, series_uid, dicomweb_headers)
    else:
        entry = sessions.get(f"{study_uid}|{series_uid}")
        if entry is None:
            raise HTTPException(409, "no active nnInteractive session; initialize first")
        entry.last_used = time.time()
    try:
        return _run_inference_request(entry, mode, data, start)

    except SessionExpiredError:
        logger.info("nnInteractive session expired for %s; recreating and retrying request once", series_uid)
        _close_entry(entry)
        retry_entry = _get_series_session(study_uid, series_uid, dicomweb_headers)
        try:
            return _run_inference_request(retry_entry, mode, data, start)
        except SessionExpiredError as e:
            _close_entry(retry_entry)
            raise HTTPException(409, "nnInteractive session expired after retry; please initialize again") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("nnInteractive proxy request failed")
        raise HTTPException(500, f"nnInteractive proxy request failed: {e}") from e
