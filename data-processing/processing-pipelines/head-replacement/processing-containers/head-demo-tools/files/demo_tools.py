#!/usr/bin/env python3
"""Minimal Task API batch tool for the head-replacement demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import SimpleITK as sitk


INPUT_ROOT = Path("/kaapana/app/input-nrrd")
BPR_ROOT = Path("/kaapana/app/bpr-json")
OUTPUT_ROOT = Path("/kaapana/app/output-nrrd")


def _one_file(directory: Path, suffix: str) -> Path:
    files = sorted(path for path in directory.iterdir() if path.name.endswith(suffix))
    if len(files) != 1:
        raise ValueError(f"Expected one {suffix} file in {directory}, found {len(files)}")
    return files[0]


def replace_head(nrrd_path: Path, bpr_path: Path, output_path: Path) -> None:
    image = sitk.DICOMOrient(sitk.ReadImage(str(nrrd_path)), "LPS")
    array = sitk.GetArrayFromImage(image)
    metadata = json.loads(bpr_path.read_text(encoding="utf-8"))
    head_indices = np.asarray(metadata["body part examined"]["head"], dtype=int)

    selected_slices = np.zeros(array.shape[0], dtype=bool)
    selected_slices[head_indices] = True
    foreground = (array > -500) & selected_slices[:, None, None]
    coordinates = np.argwhere(foreground).astype(float)
    if not len(coordinates):
        raise ValueError(f"No head foreground found for {nrrd_path}")

    spacing_zyx = np.asarray(image.GetSpacing())[::-1]
    center_zyx = coordinates.mean(axis=0)
    distances_mm = np.linalg.norm(
        (coordinates - center_zyx) * spacing_zyx, axis=1
    )
    radius_mm = np.percentile(distances_mm, 95)

    result = array.copy()
    result[foreground] = -1000
    z, y, x = np.ogrid[: array.shape[0], : array.shape[1], : array.shape[2]]
    sphere = (
        ((z - center_zyx[0]) * spacing_zyx[0]) ** 2
        + ((y - center_zyx[1]) * spacing_zyx[1]) ** 2
        + ((x - center_zyx[2]) * spacing_zyx[2]) ** 2
        <= radius_mm**2
    )
    result[sphere] = 0

    output_image = sitk.GetImageFromArray(result)
    output_image.CopyInformation(image)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(output_image, str(output_path), True)


def process_batch(input_root: Path, bpr_root: Path, output_root: Path) -> None:
    for item in sorted(path for path in input_root.iterdir() if path.is_dir()):
        item_id = item.name
        replace_head(
            _one_file(item, ".nrrd"),
            _one_file(bpr_root / item_id, ".json"),
            output_root / item_id / f"{item_id}.nrrd",
        )
        print(f"Replaced head in {item_id}", flush=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("replace-head",))
    result.add_argument("--input-root", type=Path, default=INPUT_ROOT)
    result.add_argument("--bpr-root", type=Path, default=BPR_ROOT)
    result.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    process_batch(arguments.input_root, arguments.bpr_root, arguments.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
