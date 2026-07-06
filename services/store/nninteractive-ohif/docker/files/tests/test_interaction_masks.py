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

from app.main import (  # noqa: E402
    _apply_prompts,
    _prepare_scribble,
    _preferred_scribble_radius,
    _prompt_points_and_flat_axis,
    clean_and_densify_polyline,
)


class DummyEntry:
    def __init__(self, preferred):
        self.session = types.SimpleNamespace(preferred_scribble_thickness=preferred)


class RecordingSession:
    preferred_scribble_thickness = [1, 2, 3]

    def __init__(self):
        self.scribble_calls = []

    def add_scribble_interaction(self, mask, include_interaction, interaction_bbox):
        self.scribble_calls.append((mask, include_interaction, interaction_bbox))
        return interaction_bbox


class InteractionMaskTests(unittest.TestCase):
    def test_scribble_polyline_stays_open(self):
        stroke = [[1, 1, 3], [4, 1, 3], [4, 4, 3]]
        cleaned = np.round(np.asarray(clean_and_densify_polyline(stroke, close=False))).astype(int)

        self.assertEqual(cleaned.tolist()[0], [1, 1, 3])
        self.assertEqual(cleaned.tolist()[-1], [4, 4, 3])
        self.assertNotEqual(cleaned.tolist()[0], cleaned.tolist()[-1])

    def test_lasso_polyline_closes(self):
        polygon = [[1, 1, 3], [4, 1, 3], [4, 4, 3]]
        cleaned = np.round(np.asarray(clean_and_densify_polyline(polygon, close=True))).astype(int)

        self.assertEqual(cleaned.tolist()[0], cleaned.tolist()[-1])

    def test_single_point_scribble_produces_crop(self):
        points = np.asarray([[5, 6, 2]], dtype=int)
        mask, bbox = _prepare_scribble((8, 12, 12), points, brush_radius=1, flat_axis_xyz=2)

        self.assertIsNotNone(mask)
        self.assertEqual(mask.shape, (1, 3, 3))
        self.assertEqual(int(mask.sum()), 9)
        self.assertEqual(bbox, [[2, 3], [5, 8], [4, 7]])

    def test_scribble_thickness_expands_centered_footprint(self):
        points = np.asarray([[5, 5, 2], [6, 5, 2], [7, 5, 2]], dtype=int)
        thin, thin_bbox = _prepare_scribble((8, 12, 12), points, brush_radius=0, flat_axis_xyz=2)
        thick, thick_bbox = _prepare_scribble((8, 12, 12), points, brush_radius=2, flat_axis_xyz=2)

        self.assertEqual(thin.shape, (1, 1, 3))
        self.assertEqual(int(thin.sum()), 3)
        self.assertEqual(thin_bbox, [[2, 3], [5, 6], [5, 8]])
        self.assertEqual(thick.shape, (1, 5, 7))
        self.assertEqual(int(thick.sum()), 35)
        self.assertEqual(thick_bbox, [[2, 3], [3, 8], [3, 10]])

    def test_preferred_scribble_radius_maps_xyz_to_zyx_axis(self):
        entry = DummyEntry([1, 2, 3])

        self.assertEqual(_preferred_scribble_radius(entry, 2), 1)
        self.assertEqual(_preferred_scribble_radius(entry, 1), 2)
        self.assertEqual(_preferred_scribble_radius(entry, 0), 3)

    def test_prompt_payload_carries_flat_axis(self):
        points, axis = _prompt_points_and_flat_axis({"points": [[1, 2, 3]], "axis": 2})

        self.assertEqual(points, [[1, 2, 3]])
        self.assertEqual(axis, 2)

    def test_apply_prompts_uses_payload_axis_and_preferred_thickness(self):
        session = RecordingSession()
        entry = types.SimpleNamespace(
            session=session,
            target_buffer=np.zeros((8, 12, 12), dtype=np.uint8),
            flipped=False,
            prompts_seen=set(),
            prompt_order=[],
        )

        counts, changed = _apply_prompts(
            entry,
            {"pos_scribbles": [{"points": [[5, 6, 2]], "axis": 2}]},
        )

        self.assertEqual(counts["pos_scribbles"], 1)
        self.assertEqual(changed, [[2, 3], [5, 8], [4, 7]])
        mask, include, bbox = session.scribble_calls[0]
        self.assertTrue(include)
        self.assertEqual(mask.shape, (1, 3, 3))
        self.assertEqual(int(mask.sum()), 9)
        self.assertEqual(bbox, [[2, 3], [5, 8], [4, 7]])


if __name__ == "__main__":
    unittest.main()
