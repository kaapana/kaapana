#!/usr/bin/env python3
"""
Convert a NRRD file to a DICOM series using SimpleITK,
copying metadata from a reference DICOM file or directory.

Usage:
    python nrrd_to_dicom.py -i input.nrrd -r ref_dicom_dir -o output_dir
"""

import os
import argparse
import SimpleITK as sitk
from pydicom.uid import generate_uid


def load_reference_metadata(ref_path: str):
    """Load metadata from one representative DICOM file."""
    if os.path.isdir(ref_path):
        series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(ref_path)
        if not series_ids:
            raise ValueError(f"No DICOM series found in directory: {ref_path}")
        series_files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(
            ref_path, series_ids[0]
        )
        ref_file = series_files[0]
    else:
        ref_file = ref_path

    ref_ds = sitk.ReadImage(ref_file)
    ref_keys = ref_ds.GetMetaDataKeys()
    metadata = {k: ref_ds.GetMetaData(k) for k in ref_keys}
    print(f"Loaded reference metadata from: {ref_file}")
    return metadata


def nrrd_to_dicom(input_nrrd: str, ref_path: str, output_dir: str):
    """Convert a NRRD image to a DICOM series, copying reference tags."""
    print(f"Reading NRRD image from: {input_nrrd}")
    img = sitk.ReadImage(input_nrrd)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading reference DICOM from: {ref_path}")
    ref_metadata = load_reference_metadata(ref_path)

    writer = sitk.ImageFileWriter()
    writer.KeepOriginalImageUIDOn()

    series_uid = generate_uid()
    num_slices = img.GetDepth() if img.GetDimension() == 3 else 1
    print(f"Image has {num_slices} slice(s). Writing DICOM to: {output_dir}")

    for i in range(num_slices):
        slice_img = img[:, :, i] if num_slices > 1 else img

        # Copy reference metadata
        for tag, value in ref_metadata.items():
            slice_img.SetMetaData(tag, value)

        # Override key DICOM tags to maintain uniqueness
        slice_img.SetMetaData("0008|0018", generate_uid())  # SOPInstanceUID
        slice_img.SetMetaData("0020|000e", series_uid)  # SeriesInstanceUID
        slice_img.SetMetaData("0020|0013", str(i + 1))  # InstanceNumber

        # Write the slice
        out_file = os.path.join(output_dir, f"slice_{i:04d}.dcm")
        writer.SetFileName(out_file)
        writer.Execute(slice_img)

    print(f"DICOM conversion complete. Files written to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert NRRD to DICOM using a reference DICOM for metadata."
    )
    parser.add_argument("-i", "--input", required=True, help="Input NRRD file path.")
    parser.add_argument(
        "-r", "--reference", required=True, help="Reference DICOM file or directory."
    )
    parser.add_argument("-o", "--output", required=True, help="Output DICOM directory.")
    args = parser.parse_args()

    nrrd_to_dicom(args.input, args.reference, args.output)
