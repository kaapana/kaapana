import sys
import types
import unittest
from pathlib import Path

import numpy as np


def _install_nninteractive_stub() -> None:
    remote = types.ModuleType("nnInteractive.inference.remote")

    class DummySession:
        pass

    class DummyServerAtCapacityError(Exception):
        pass

    class DummySessionExpiredError(Exception):
        pass

    remote.nnInteractiveRemoteInferenceSession = DummySession
    remote.ServerAtCapacityError = DummyServerAtCapacityError
    remote.SessionExpiredError = DummySessionExpiredError

    inference = types.ModuleType("nnInteractive.inference")
    inference.remote = remote
    package = types.ModuleType("nnInteractive")
    package.inference = inference

    sys.modules.setdefault("nnInteractive", package)
    sys.modules.setdefault("nnInteractive.inference", inference)
    sys.modules.setdefault("nnInteractive.inference.remote", remote)


_install_nninteractive_stub()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException  # noqa: E402

import base64  # noqa: E402
import gzip  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402

import app.main as proxy  # noqa: E402
from app.main import (  # noqa: E402
    CachedImage,
    _client_session_id,
    _gunzip_limited,
    _principal,
    _reserve_capacity,
    _validate_shape,
    _apply_prompts,
    _bbox_to_half_open_intervals,
    _prepare_lasso,
    _prepare_scribble,
    _preferred_brush_size,
    _prompt_points_and_flat_axis,
    _resolve_flip,
)


class DummyEntry:
    def __init__(self, preferred):
        self.session = types.SimpleNamespace(preferred_scribble_thickness=preferred)


class RecordingSession:
    preferred_scribble_thickness = [1, 2, 3]

    def __init__(self):
        self.calls = []

    def add_point_interaction(self, coordinates, include_interaction):
        self.calls.append(("point", coordinates, include_interaction))
        return None

    def add_bbox_interaction(self, bbox, include_interaction):
        self.calls.append(("bbox", bbox, include_interaction))
        return None

    def add_scribble_interaction(self, mask, include_interaction, interaction_bbox):
        self.calls.append(("scribble", mask, include_interaction, interaction_bbox))
        return interaction_bbox

    def add_lasso_interaction(self, mask, include_interaction, interaction_bbox):
        self.calls.append(("lasso", mask, include_interaction, interaction_bbox))
        return interaction_bbox


def _entry(session, shape=(8, 12, 12), flipped=False):
    return types.SimpleNamespace(
        session=session,
        target_buffer=np.zeros(shape, dtype=np.uint8),
        flipped=flipped,
        spacing_zyx=(1.0, 1.0, 1.0),
        prompts_seen=set(),
        prompt_order=[],
    )


class InteractionMaskTests(unittest.TestCase):
    """Prompt geometry must match the napari-nninteractive plugin."""

    def test_brush_size_two_paints_napari_square(self):
        # napari: radius floor(2 / 2) + 0.5 = 1.5 -> a full 3x3 stamp.
        mask, bbox = _prepare_scribble((8, 12, 12), np.asarray([[2.0, 6.0, 5.0]]), 0, 2, (1.0, 1.0, 1.0))

        self.assertEqual(mask.shape, (1, 3, 3))
        self.assertEqual(int(mask.sum()), 9)
        self.assertEqual(bbox, [[2, 3], [5, 8], [4, 7]])

    def test_brush_follows_spacing_on_anisotropic_plane(self):
        # Coronal plane (y fixed) with 3 mm slices and 1 mm pixels: one voxel thick along z.
        mask, bbox = _prepare_scribble((8, 12, 12), np.asarray([[4.0, 6.0, 5.0]]), 1, 2, (3.0, 1.0, 1.0))

        self.assertEqual(mask.shape, (1, 1, 3))
        self.assertEqual(bbox, [[4, 5], [6, 7], [4, 7]])

    def test_scribble_stroke_is_continuous_and_on_its_slice(self):
        stroke = np.asarray([[2.2, 5.0, 1.0], [2.2, 5.0, 9.0]])
        mask, bbox = _prepare_scribble((8, 12, 12), stroke, 0, 2, (1.0, 1.0, 1.0))

        self.assertEqual(bbox, [[2, 3], [4, 7], [0, 11]])
        self.assertEqual(int(mask.sum()), 3 * 11)

    def test_lasso_uses_floor_ceil_crop_and_polygon_fill(self):
        polygon = np.asarray([[3.0, 2.0, 2.0], [3.0, 2.0, 6.0], [3.0, 6.0, 6.0], [3.0, 6.0, 2.0]])
        mask, bbox = _prepare_lasso((8, 12, 12), polygon, 0)

        self.assertEqual(bbox, [[3, 4], [2, 7], [2, 7]])
        self.assertEqual(mask.shape, (1, 5, 5))
        self.assertEqual(int(mask.sum()), 25)

    def test_box_is_half_open_like_napari(self):
        corners = np.asarray([[4.0, 2.4, 3.6], [4.0, 7.5, 9.2]])

        self.assertEqual(_bbox_to_half_open_intervals(corners), [[4.0, 5.0], [2.4, 7.5], [3.6, 9.2]])

    def test_preferred_brush_size_is_per_zyx_axis(self):
        entry = DummyEntry([1, 2, 3])

        self.assertEqual(_preferred_brush_size(entry, 0), 1.0)
        self.assertEqual(_preferred_brush_size(entry, 2), 3.0)
        self.assertEqual(_preferred_brush_size(DummyEntry(2), 1), 2.0)

    def test_prompt_payload_carries_flat_axis(self):
        points, axis = _prompt_points_and_flat_axis({"points": [[1, 2, 3]], "axis": 2})

        self.assertEqual(points, [[1, 2, 3]])
        self.assertEqual(axis, 2)

    def test_points_and_boxes_reach_the_session_unrounded_and_flipped(self):
        session = RecordingSession()
        entry = _entry(session, flipped=True)

        _apply_prompts(entry, {"pos_points": [[5.4, 6.6, 2]], "neg_boxes": [[[1.2, 2.7, 3], [4.8, 5.1, 3]]]})

        self.assertEqual(session.calls[0], ("point", [5.0, 6.6, 5.4], True))
        self.assertEqual(session.calls[1], ("bbox", [[4.0, 5.0], [2.7, 5.1], [1.2, 4.8]], False))

    def test_scribble_uses_payload_axis_and_preferred_thickness(self):
        session = RecordingSession()
        entry = _entry(session)

        counts, changed = _apply_prompts(entry, {"pos_scribbles": [{"points": [[5, 6, 2]], "axis": 2}]})

        self.assertEqual(counts["pos_scribbles"], 1)
        _, mask, include, bbox = session.calls[0]
        self.assertTrue(include)
        # Thickness 1 along z: radius floor(0.5) + 0.5 = 0.5 -> a one-voxel brush.
        self.assertEqual(mask.shape, (1, 1, 1))
        self.assertEqual(bbox, [[2, 3], [6, 7], [5, 6]])
        self.assertEqual(changed, bbox)


class SliceOrderTests(unittest.TestCase):
    def _image(self, instance_number_flipped=False):
        return CachedImage(np.zeros((1, 2, 1, 1)), "sop-low", "sop-high", instance_number_flipped, {})

    def test_viewer_order_matches_volume(self):
        self.assertFalse(_resolve_flip(self._image(instance_number_flipped=True), "sop-low"))

    def test_viewer_order_reversed(self):
        # OHIF sorts by position; InstanceNumber ascending along the volume must not hide the reversal.
        self.assertTrue(_resolve_flip(self._image(instance_number_flipped=False), "sop-high"))

    def test_unknown_first_slice_is_rejected(self):
        with self.assertRaises(HTTPException):
            _resolve_flip(self._image(), "sop-other")

    def test_missing_client_order_falls_back_to_instance_number(self):
        self.assertTrue(_resolve_flip(self._image(instance_number_flipped=True), None))


class RequestGuardTests(unittest.TestCase):
    def test_client_session_id_is_required(self):
        with self.assertRaises(HTTPException) as ctx:
            _client_session_id("")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(_client_session_id(" tab-1 "), "tab-1")

    def test_shape_mismatch_is_rejected(self):
        image = CachedImage(np.zeros((1, 3, 4, 5)), "a", "b", False, {})
        _validate_shape(image, [3, 4, 5])
        _validate_shape(image, None)  # older clients send no shape
        with self.assertRaises(HTTPException) as ctx:
            _validate_shape(image, [3, 5, 4])
        self.assertEqual(ctx.exception.status_code, 422)

    def test_gunzip_limited(self):
        data = gzip.compress(b"\0" * 100)
        self.assertEqual(_gunzip_limited(data, 100), b"\0" * 100)
        with self.assertRaises(HTTPException):
            _gunzip_limited(data, 99)
        with self.assertRaises(HTTPException):
            _gunzip_limited(b"not gzip", 100)


def _request(headers):
    return types.SimpleNamespace(headers={k.lower(): v for k, v in headers.items()})


def _token(claims):
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"h.{body}.s"


class PrincipalTests(unittest.TestCase):
    def test_subject_and_project_scope_the_principal(self):
        alice = _principal(_request({"Authorization": f"Bearer {_token({'sub': 'alice'})}", "Project": "p1"}))
        self.assertEqual(alice, "alice|p1")
        other_project = _principal(_request({"Authorization": f"Bearer {_token({'sub': 'alice'})}", "Project": "p2"}))
        self.assertNotEqual(alice, other_project)

    def test_forwarded_token_and_anonymous(self):
        self.assertEqual(_principal(_request({"X-Forwarded-Access-Token": _token({"sub": "bob"})})), "bob|")
        self.assertEqual(_principal(_request({})), "anonymous|")


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self._saved = dict(proxy.sessions)
        proxy.sessions.clear()

    def tearDown(self):
        proxy.sessions.clear()
        proxy.sessions.update(self._saved)

    def _entry(self, key, idle_seconds):
        seen = time.time() - idle_seconds
        closed = []
        session = types.SimpleNamespace(close=lambda: closed.append(key))
        entry = types.SimpleNamespace(
            key=key, series_uid=key, session=session, last_used=seen, last_browser_seen=seen,
            lock=proxy.threading.RLock(), closed=closed,
        )
        proxy.sessions[key] = entry
        return entry

    def test_abandoned_sessions_are_reaped(self):
        stale = self._entry("stale", proxy.STALE_SESSION_SECONDS + 10)
        for i in range(proxy.MAX_CACHED_SESSIONS - 1):
            self._entry(f"live{i}", 0)
        _reserve_capacity()
        self.assertNotIn("stale", proxy.sessions)
        self.assertEqual(stale.closed, ["stale"])

    def test_full_with_active_sessions_refuses_instead_of_evicting(self):
        for i in range(proxy.MAX_CACHED_SESSIONS):
            self._entry(f"live{i}", 0)
        with self.assertRaises(HTTPException) as ctx:
            _reserve_capacity()
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(len(proxy.sessions), proxy.MAX_CACHED_SESSIONS)


if __name__ == "__main__":
    unittest.main()
