from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).parents[1] / "files" / "run_bpreg.py"
SPEC = importlib.util.spec_from_file_location("run_bpreg", MODULE_PATH)
assert SPEC and SPEC.loader
run_bpreg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_bpreg)


def add_nrrd(root: Path, item_id: str, filename: str) -> Path:
    item_dir = root / item_id
    item_dir.mkdir(parents=True, exist_ok=True)
    nrrd_path = item_dir / filename
    nrrd_path.touch()
    return nrrd_path


class BodyPartRegressionTaskTest(unittest.TestCase):
    def test_processes_all_files_with_one_model_and_preserves_names(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_root = root / "nrrd"
            output_root = root / "bpr-json"
            add_nrrd(input_root, "series-b", "volume.nrrd")
            add_nrrd(input_root, "series-a", "first.nrrd")
            add_nrrd(input_root, "series-a", "second.nrrd")

            model = Mock()
            temporary_niftis = []

            def convert(nrrd_path, nifti_path):
                temporary_niftis.append(nifti_path)
                nifti_path.touch()

            def infer(**kwargs):
                self.assertTrue(Path(kwargs["nifti_path"]).is_file())
                Path(kwargs["output_path"]).write_text(
                    '{"result": "native"}\n', encoding="utf-8"
                )

            model.nifti2json.side_effect = infer

            with (
                patch.object(run_bpreg, "load_model", return_value=model) as loader,
                patch.object(run_bpreg, "nrrd_to_nifti", side_effect=convert) as converter,
            ):
                processed = run_bpreg.process_batch(
                    input_root,
                    output_root,
                    root / "model",
                    True,
                )

            self.assertEqual(processed, 3)
            loader.assert_called_once_with(root / "model", True)
            self.assertEqual(
                [call.args[0] for call in converter.call_args_list],
                [
                    input_root / "series-a" / "first.nrrd",
                    input_root / "series-a" / "second.nrrd",
                    input_root / "series-b" / "volume.nrrd",
                ],
            )
            self.assertEqual(
                [call.kwargs["output_path"] for call in model.nifti2json.call_args_list],
                [
                    str(output_root / "series-a" / "first.json"),
                    str(output_root / "series-a" / "second.json"),
                    str(output_root / "series-b" / "volume.json"),
                ],
            )
            self.assertTrue(
                all(
                    call.kwargs["stringify_json"] is False
                    for call in model.nifti2json.call_args_list
                )
            )
            self.assertTrue(all(not path.exists() for path in temporary_niftis))
            self.assertTrue((output_root / "series-a" / "first.json").is_file())
            self.assertTrue((output_root / "series-a" / "second.json").is_file())
            self.assertTrue((output_root / "series-b" / "volume.json").is_file())

    def test_orients_nrrd_to_lps_before_writing_nifti(self):
        source_image = Mock()
        oriented_image = Mock()
        simple_itk = Mock()
        simple_itk.ReadImage.return_value = source_image
        simple_itk.DICOMOrient.return_value = oriented_image

        with patch.object(run_bpreg, "sitk", simple_itk):
            run_bpreg.nrrd_to_nifti(Path("scan.nrrd"), Path("scan.nii.gz"))

        simple_itk.ReadImage.assert_called_once_with("scan.nrrd")
        simple_itk.DICOMOrient.assert_called_once_with(source_image, "LPS")
        simple_itk.WriteImage.assert_called_once_with(
            oriented_image, "scan.nii.gz", True
        )

    def test_fails_when_no_nrrd_was_processed(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_root = root / "nrrd"
            input_root.mkdir()

            with patch.object(run_bpreg, "load_model", return_value=Mock()):
                with self.assertRaisesRegex(RuntimeError, "No .nrrd files"):
                    run_bpreg.process_batch(
                        input_root,
                        root / "bpr-json",
                        root / "model",
                        False,
                    )


if __name__ == "__main__":
    unittest.main()
