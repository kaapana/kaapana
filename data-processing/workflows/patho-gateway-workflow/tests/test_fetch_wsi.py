import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = (
    Path(__file__).parents[1]
    / "processing-containers"
    / "wsi-fetcher"
    / "files"
    / "fetch_wsi.py"
)


def load_fetch_wsi_module():
    spec = importlib.util.spec_from_file_location("fetch_wsi", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FetchWsiTest(unittest.TestCase):
    def test_parse_slide_ids_accepts_list_and_comma_separated_string(self):
        module = load_fetch_wsi_module()

        self.assertEqual(
            module.parse_slide_ids(["SLIDE_001", " SLIDE_002 "]),
            ["SLIDE_001", "SLIDE_002"],
        )
        self.assertEqual(
            module.parse_slide_ids("SLIDE_001, SLIDE_002"),
            ["SLIDE_001", "SLIDE_002"],
        )

    def test_parse_slide_ids_rejects_missing_or_empty_values(self):
        module = load_fetch_wsi_module()

        with self.assertRaisesRegex(RuntimeError, "missing"):
            module.parse_slide_ids(None)
        with self.assertRaisesRegex(RuntimeError, "empty"):
            module.parse_slide_ids("")
        with self.assertRaisesRegex(RuntimeError, "empty"):
            module.parse_slide_ids([])

    def test_filesystem_fetch_writes_files_and_manifest(self):
        module = load_fetch_wsi_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            input_dir.mkdir()
            (input_dir / "SLIDE_001.svs").write_bytes(b"svs")
            slide_folder = input_dir / "SLIDE_002"
            slide_folder.mkdir()
            (slide_folder / "SLIDE_002.dcm").write_bytes(b"dicom")

            module.main(
                output_dir,
                {
                    "slide_ids": "SLIDE_001,SLIDE_002",
                    "wsi_source": "filesystem",
                    "wsi_input_dir": str(input_dir),
                }
            )

            self.assertEqual((output_dir / "SLIDE_001.svs").read_bytes(), b"svs")
            self.assertEqual((output_dir / "SLIDE_002.dcm").read_bytes(), b"dicom")
            manifest = json.loads((output_dir / "manifest.json").read_text())
            self.assertEqual(
                manifest,
                {
                    "items": [
                        {
                            "slide_id": "SLIDE_001",
                            "local_filename": "SLIDE_001.svs",
                            "source": "filesystem",
                            "detected_format": "svs",
                        },
                        {
                            "slide_id": "SLIDE_002",
                            "local_filename": "SLIDE_002.dcm",
                            "source": "filesystem",
                            "detected_format": "dcm",
                        },
                    ]
                },
            )

    def test_filesystem_fetch_fails_for_unresolved_slide_id(self):
        module = load_fetch_wsi_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            input_dir.mkdir()

            with self.assertRaisesRegex(RuntimeError, "could not be resolved"):
                module.main(
                    output_dir,
                    {
                        "slide_ids": ["MISSING"],
                        "wsi_source": "filesystem",
                        "wsi_input_dir": str(input_dir),
                    }
                )

    def test_object_storage_fetch_uses_slide_ids_as_files_or_folders(self):
        module = load_fetch_wsi_module()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            client = FakeObjectStoreClient(
                {
                    "pathology/SLIDE_001.svs": b"svs",
                    "pathology/SLIDE_002/SLIDE_002.dcm": b"dicom",
                }
            )

            with patch.object(module, "get_external_object_store_client", return_value=client):
                module.main(
                    output_dir,
                    {
                        "slide_ids": ["SLIDE_001", "SLIDE_002"],
                        "wsi_source": "object-storage",
                        "object_storage_endpoint": "external-object-store.example.org:9000",
                        "object_storage_bucket": "pathology-wsi",
                        "object_storage_prefix": "pathology",
                        "object_storage_access_key": "access",
                        "object_storage_secret_key": "secret",
                    }
                )

            self.assertEqual((output_dir / "SLIDE_001.svs").read_bytes(), b"svs")
            self.assertEqual((output_dir / "SLIDE_002.dcm").read_bytes(), b"dicom")
            manifest = json.loads((output_dir / "manifest.json").read_text())
            self.assertEqual(
                [item["source"] for item in manifest["items"]],
                ["object-storage", "object-storage"],
            )


class FakeObjectStoreObject:
    def __init__(self, object_name, is_dir=False):
        self.object_name = object_name
        self.is_dir = is_dir


class FakeObjectStoreClient:
    def __init__(self, objects):
        self.objects = objects

    def stat_object(self, bucket, object_name):
        if object_name not in self.objects:
            raise FileNotFoundError(object_name)

    def list_objects(self, bucket, prefix, recursive=True):
        return [
            FakeObjectStoreObject(object_name)
            for object_name in self.objects
            if object_name.startswith(prefix)
        ]

    def fget_object(self, bucket, object_name, target):
        Path(target).write_bytes(self.objects[object_name])


if __name__ == "__main__":
    unittest.main()
