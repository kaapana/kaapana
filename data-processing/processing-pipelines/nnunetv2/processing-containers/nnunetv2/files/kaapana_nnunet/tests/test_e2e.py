"""End to end on CPU: DICOM -> create_dataset -> plan_preprocess -> train (two folds) with real nnU-Net.

Every step runs with fresh, empty pod folders and gets its inputs only from S3, like separate pods.
DICOMweb and the metadata index are replaced by local fakes. Slow (minutes); needs nnunetv2 + torch:

    NNUNET_TEST_S3=127.0.0.1:19000 NNUNET_TEST_E2E=1 pytest tests/test_e2e.py
"""

import json
import os
import shutil
import subprocess
import sys
import types
import uuid

import numpy as np
import pydicom
import pytest
from pydicom.dataset import FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from tests.conftest import ENDPOINT

pytestmark = pytest.mark.skipif(
    not (ENDPOINT and os.environ.get("NNUNET_TEST_E2E")), reason="set NNUNET_TEST_S3 and NNUNET_TEST_E2E=1"
)
hd = pytest.importorskip("highdicom")
pytest.importorskip("nnunetv2")

SHAPE = (12, 40, 40)  # z, y, x
N_CASES = 6
STUDY_TAG, SERIES_TAG = "0020000D StudyInstanceUID_keyword", "0020000E SeriesInstanceUID_keyword"


def write_case(root, n, rng):
    """One study with a CT and a SEG (labels 'liver' and, in odd cases, 'Tumour')."""
    study, series, frame = generate_uid(), generate_uid(), generate_uid()
    z, y, x = np.ogrid[: SHAPE[0], : SHAPE[1], : SHAPE[2]]
    center = np.array(SHAPE) / 2 + rng.integers(-3, 4, 3)
    ball = ((z - center[0]) * 2) ** 2 + (y - center[1]) ** 2 + (x - center[2]) ** 2 < 12**2
    volume = (rng.normal(0, 20, SHAPE) + ball * 120).astype(np.int16)
    tumour = np.zeros(SHAPE, bool)
    if n % 2:
        tumour[5:8, 18:23, 18:23] = True
    datasets = []
    (root / series).mkdir(parents=True)
    for k in range(SHAPE[0]):
        ds = pydicom.Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds.file_meta.MediaStorageSOPClassUID = ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
        ds.PatientName, ds.PatientID, ds.PatientBirthDate, ds.PatientSex = "Test^E2E", f"P{n}", "", "O"
        ds.StudyInstanceUID, ds.SeriesInstanceUID, ds.FrameOfReferenceUID = study, series, frame
        ds.StudyID, ds.StudyDate, ds.StudyTime, ds.AccessionNumber, ds.ReferringPhysicianName = "1", "", "", "", ""
        ds.Modality, ds.SeriesNumber, ds.InstanceNumber, ds.Manufacturer = "CT", 1, k + 1, "test"
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.ImagePositionPatient = [0.0, 0.0, 2.0 * k]
        ds.PixelSpacing, ds.SliceThickness = [1.0, 1.0], 2.0
        ds.Rows, ds.Columns = SHAPE[1], SHAPE[2]
        ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
        ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 16, 15, 1
        ds.RescaleIntercept, ds.RescaleSlope = 0, 1
        ds.PixelData = volume[k].tobytes()
        ds.save_as(root / series / f"{k}.dcm", enforce_file_format=True)
        datasets.append(ds)
    names = {"liver": ball & ~tumour, "Tumour": tumour} if n % 2 else {"liver": ball}
    seg = hd.seg.Segmentation(
        source_images=datasets,
        pixel_array=np.stack(list(names.values()), -1).astype(np.uint8),
        segmentation_type=hd.seg.SegmentationTypeValues.BINARY,
        segment_descriptions=[
            hd.seg.SegmentDescription(
                segment_number=i + 1,
                segment_label=name,
                segmented_property_category=hd.sr.CodedConcept("91723000", "SCT", "Anatomical Structure"),
                segmented_property_type=hd.sr.CodedConcept("10200004", "SCT", "Liver"),
                algorithm_type=hd.seg.SegmentAlgorithmTypeValues.MANUAL,
            )
            for i, name in enumerate(names)
        ],
        series_instance_uid=generate_uid(),
        series_number=2,
        sop_instance_uid=generate_uid(),
        instance_number=1,
        manufacturer="test",
        manufacturer_model_name="test",
        software_versions="1",
        device_serial_number="1",
    )
    (root / seg.SeriesInstanceUID).mkdir()
    seg.save_as(root / seg.SeriesInstanceUID / "seg.dcm")
    meta = lambda uid, mod: {STUDY_TAG: study, SERIES_TAG: uid, "00080060 Modality_keyword": mod}  # noqa: E731
    return [meta(series, "CT"), meta(seg.SeriesInstanceUID, "SEG")]


@pytest.fixture
def pacs(tmp_path, monkeypatch):
    rng = np.random.default_rng(0)
    root = tmp_path / "pacs"
    metas = [m for n in range(N_CASES) for m in write_case(root, n, rng)]

    class FakeDcmWeb:
        def download_series(self, study_uid, series_uid, target_dir):
            shutil.copytree(root / series_uid, target_dir, dirs_exist_ok=True)
            return True

    module = types.ModuleType("kaapana_client.helper.HelperDcmWeb")
    module.HelperDcmWeb = FakeDcmWeb
    for name in ("kaapana_client", "kaapana_client.helper"):
        monkeypatch.setitem(sys.modules, name, sys.modules.get(name) or types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "kaapana_client.helper.HelperDcmWeb", module)

    from kaapana_nnunet import sources

    class FakeMetadata:
        def __init__(self, index):
            pass

        def series(self, uids):
            return {m[SERIES_TAG]: m for m in metas if m[SERIES_TAG] in uids}

        def study_series(self, study_uid):
            return [m for m in metas if m[STUDY_TAG] == study_uid]

    monkeypatch.setattr(sources, "Metadata", FakeMetadata)
    return metas


def run_step(module, store, tmp_path, monkeypatch, form, identifiers=(), env=None):
    """A fresh 'pod': new workflow dir, new /nnunet root."""
    from kaapana_nnunet.context import Context

    pod = tmp_path / f"pod-{uuid.uuid4().hex[:6]}"
    monkeypatch.setenv("WORKFLOW_DIR", str(pod / "workflow"))
    monkeypatch.setenv("NNUNET_POD_ROOT", str(pod / "nnunet"))
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    conf = {
        "workflow_form": form,
        "project_form": {"s3_bucket": store.bucket, "opensearch_index": "project_test"},
        "data_form": {"identifiers": list(identifiers)},
    }
    ctx = Context(conf=conf)
    ctx._store = store
    try:
        module.run(ctx)
    finally:
        ctx.cleanup()


def test_dicom_to_trained_folds(store, tmp_path, monkeypatch, pacs):
    from kaapana_nnunet import catalog, layout
    from kaapana_nnunet.steps import create_dataset, plan_preprocess, train
    from kaapana_nnunet.store import NotPublished

    ids = [m[SERIES_TAG] for m in pacs]

    # dry run uploads nothing
    run_step(create_dataset, store, tmp_path, monkeypatch, {"dataset_name": "Liver", "check_only": True}, ids)
    assert store.list_markers("raw") == []

    labels = [{"name": "liver"}, {"name": "tumor", "aliases": "Tumour, lesion"}]
    run_step(create_dataset, store, tmp_path, monkeypatch, {"dataset_name": "Liver", "labels": labels}, ids)
    (raw,) = store.list_markers("raw")
    assert raw["prefix"] == "raw/Dataset001_Liver"
    dataset_json = json.loads(
        store._client().get_object(store.bucket, "nnunet/raw/Dataset001_Liver/dataset.json").read()
    )
    assert dataset_json["labels"] == {"background": 0, "liver": 1, "tumor": 2}
    assert dataset_json["channel_names"] == {"0": "CT"} and dataset_json["numTraining"] == N_CASES

    form = {"task_ids": "Dataset001_Liver", "configurations": ["3d_fullres"], "verify_dataset_integrity": True}
    run_step(plan_preprocess, store, tmp_path, monkeypatch, form)
    units = {m["unit"] for m in store.list_markers("preprocessed")}
    assert units == {"fingerprint", "plans.nnUNetPlans", "data.nnUNetPlans_3d_fullres"}
    (pre,) = catalog.entries(store)[catalog.KIND_PREPROCESSED].values()
    assert pre["task_ids"] == "Dataset001_Liver|nnUNetPlans|3d_fullres"

    trainer = os.environ.get("NNUNET_E2E_TRAINER", "nnUNetTrainer_1epoch")
    for fold in ("0", "1", "2", "3", "4"):
        run_step(
            train,
            store,
            tmp_path,
            monkeypatch,
            {"task_ids": pre["task_ids"], "trainer": trainer, "npz": True},
            env={"NNUNET_FOLD": fold, "NNUNET_DEVICE": "cpu", "nnUNet_n_proc_DA": "2"},
        )
    model = layout.results_prefix("Dataset001_Liver", trainer, "nnUNetPlans", "3d_fullres")
    for fold in ("0", "1", "2", "3", "4"):
        marker = store.read_marker(model, f"fold_{fold}")
        paths = {e["path"] for e in marker["files"]}
        assert f"fold_{fold}/checkpoint_final.safetensors" in paths
        assert f"fold_{fold}/validation/summary.json" in paths
        assert {"dataset.json", "plans.json", "dataset_fingerprint.json", "kaapana.json"} <= paths
        with pytest.raises(NotPublished):
            store.read_marker(model, f"progress.fold_{fold}")
    (entry,) = catalog.entries(store)[catalog.KIND_MODEL].values()
    assert entry["info"] == "folds 0, 1, 2, 3, 4"

    # the two folds trained in separate pods on the published split: their validation sets are disjoint
    splits = json.loads(
        store._client().get_object(store.bucket, "nnunet/preprocessed/Dataset001_Liver/splits_final.json").read()
    )
    assert set(splits[0]["val"]).isdisjoint(splits[1]["val"])

    # cross-validation summary + postprocessing, then prediction of the (training) images back to "the PACS"
    from kaapana_nnunet.steps import find_best_config, predict

    run_step(find_best_config, store, tmp_path, monkeypatch, {"task_ids": model})
    (best,) = [m for m in store.list_markers("results/Dataset001_Liver") if (m["unit"] or "").startswith("best.")]
    assert any(
        e["path"].endswith("crossval_results_folds_0_1_2_3_4/postprocessing.pkl") for e in best["marker"]["files"]
    )

    received = tmp_path / "pacs-received"
    received.mkdir()
    port = str(20000 + os.getpid() % 10000)
    scp = subprocess.Popen(["storescp", "-od", str(received), port])
    try:
        ct = [m[SERIES_TAG] for m in pacs if m["00080060 Modality_keyword"] == "CT"]
        run_step(
            predict,
            store,
            tmp_path,
            monkeypatch,
            {"task_ids": model},
            identifiers=ct[:2],
            env={"NNUNET_DEVICE": "cpu", "PACS_HOST": "127.0.0.1", "PACS_PORT": port},
        )
    finally:
        scp.terminate()
        scp.wait()
    segs = [pydicom.dcmread(f) for f in received.iterdir()]
    assert len(segs) == 2
    for seg in segs:
        assert seg.Modality == "SEG"
        assert dicom_ref(seg) in ct[:2]
        assert {s.SegmentLabel for s in seg.SegmentSequence} <= {"liver", "tumor"}


def dicom_ref(seg):
    return seg.ReferencedSeriesSequence[0].SeriesInstanceUID
