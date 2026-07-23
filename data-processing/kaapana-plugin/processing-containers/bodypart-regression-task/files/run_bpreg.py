from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence

import SimpleITK as sitk


LOGGER = logging.getLogger("bodypartregression-task")


def load_model(model_dir: Path, gpu: bool):
    from bpreg.inference.inference_model import InferenceModel

    # The pinned implementation concatenates model filenames to this path.
    return InferenceModel(
        f"{model_dir.resolve()}{os.sep}",
        gpu=gpu,
        warning_to_error=True,
    )


def nrrd_to_nifti(nrrd_path: Path, nifti_path: Path) -> None:
    image = sitk.ReadImage(str(nrrd_path))
    image = sitk.DICOMOrient(image, "LPS")
    sitk.WriteImage(image, str(nifti_path), True)


def process_batch(
    input_root: Path,
    output_root: Path,
    model_dir: Path,
    gpu: bool,
) -> int:
    """Run the upstream model for every NRRD in every Task API item."""

    model = load_model(model_dir, gpu)
    processed = 0

    for item_dir in sorted(input_root.iterdir()):
        if not item_dir.is_dir():
            continue

        for nrrd_path in sorted(item_dir.glob("*.nrrd")):
            if not nrrd_path.is_file():
                continue

            item_output = output_root / item_dir.name
            item_output.mkdir(parents=True, exist_ok=True)
            output_path = item_output / f"{nrrd_path.stem}.json"

            with TemporaryDirectory(prefix="bodypartregression-") as temp_dir:
                nifti_path = Path(temp_dir) / f"{nrrd_path.stem}.nii.gz"
                nrrd_to_nifti(nrrd_path, nifti_path)
                model.nifti2json(
                    nifti_path=str(nifti_path),
                    output_path=str(output_path),
                    stringify_json=False,
                )
            processed += 1
            LOGGER.info("Processed %s", nrrd_path)

    if processed == 0:
        raise RuntimeError(f"No .nrrd files found below {input_root}")
    return processed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run BodyPartRegression over Task API item directories."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("/kaapana/app/nrrd"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/kaapana/app/bpr-json"),
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path(
            "/kaapana/app/BodyPartRegression/src/models/public_bpr_model"
        ),
    )
    parser.add_argument("--gpu", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args(argv)
    processed = process_batch(
        input_root=args.input_root,
        output_root=args.output_root,
        model_dir=args.model_dir,
        gpu=args.gpu,
    )
    LOGGER.info("Processed %d BodyPartRegression file(s)", processed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
