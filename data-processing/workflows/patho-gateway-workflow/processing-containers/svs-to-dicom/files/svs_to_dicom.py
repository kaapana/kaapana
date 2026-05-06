#!/usr/bin/env python3

import os
import sys
from pathlib import Path

import pydicom
from wsidicomizer import WsiDicomizer
from wsidicomizer.sources import TiffSlideSource
from wsidicomizer.metadata import WsiDicomizerMetadata

from wsidicom.conceptcode import (
    AnatomicPathologySpecimenTypesCode,
    ContainerTypeCode,
    SpecimenCollectionProcedureCode,
    SpecimenEmbeddingMediaCode,
    SpecimenFixativesCode,
    SpecimenSamplingProcedureCode,
    SpecimenStainsCode,
)
from wsidicom.metadata import (
    Collection,
    Embedding,
    Equipment,
    Fixation,
    Label,
    Patient,
    Sample,
    Series,
    Slide,
    SlideSample,
    Specimen,
    Staining,
    Study,
)


INPUT_DIR = Path("/kaapana/mount/wsi")
OUTPUT_DIR = Path("/kaapana/mount/dicom")


def log(message):
    print(message, flush=True)


def fail(message):
    raise RuntimeError(message)


study = Study(identifier="Study identifier")
series = Series(number=1)
label = Label(text="Label text")

equipment = Equipment(
    manufacturer="Kaapana",
    model_name="Scanner model name",
    device_serial_number="Scanner serial number",
    software_versions=["Scanner software versions"],
)

specimen = Specimen(
    identifier="Specimen",
    extraction_step=Collection(
        method=SpecimenCollectionProcedureCode("Excision")
    ),
    type=AnatomicPathologySpecimenTypesCode("Gross specimen"),
    container=ContainerTypeCode("Specimen container"),
    steps=[
        Fixation(
            fixative=SpecimenFixativesCode("Neutral Buffered Formalin")
        )
    ],
)

block = Sample(
    identifier="Block",
    sampled_from=[
        specimen.sample(
            method=SpecimenSamplingProcedureCode("Dissection")
        )
    ],
    type=AnatomicPathologySpecimenTypesCode("tissue specimen"),
    container=ContainerTypeCode("Tissue cassette"),
    steps=[
        Embedding(
            medium=SpecimenEmbeddingMediaCode("Paraffin wax")
        )
    ],
)

slide_sample = SlideSample(
    identifier="Slide sample",
    sampled_from=block.sample(
        method=SpecimenSamplingProcedureCode("Block sectioning")
    ),
)

slide = Slide(
    identifier="Slide",
    stainings=[
        Staining(
            substances=[
                SpecimenStainsCode("hematoxylin stain"),
                SpecimenStainsCode("water soluble eosin stain"),
            ]
        )
    ],
    samples=[slide_sample],
)


def build_metadata(file_name: str):
    return WsiDicomizerMetadata(
        study=study,
        series=series,
        patient=Patient(name=file_name),
        equipment=equipment,
        slide=slide,
        label=label,
    )


def postprocess_dicom_files(output_dcm_dir: Path):
    dicom_files = sorted(output_dcm_dir.glob("*.dcm"))

    counter = 0
    kept_files = []

    for dicom_file in dicom_files:
        ds = pydicom.dcmread(dicom_file)

        instance_number = ds.InstanceNumber
        new_filename = f"instance_{instance_number}_a{counter}.dcm"
        new_filepath = dicom_file.parent / new_filename

        dicom_file.rename(new_filepath)

        if len(ds.ImageType) > 2 and ds.ImageType[2] == "THUMBNAIL":
            new_filepath.unlink()
        else:
            kept_files.append(new_filepath)

        counter += 1

    return kept_files


def convert_wsi_file(input_file: Path):
    file_name = input_file.name.replace(".", "")
    output_dcm_dir = OUTPUT_DIR / file_name
    output_dcm_dir.mkdir(parents=True, exist_ok=True)

    metadata = build_metadata(file_name)

    try:
        WsiDicomizer.convert(
            input_file,
            output_dcm_dir,
            metadata=metadata,
            add_missing_levels=True,
            include_confidential=False,
        )
    except Exception as exc:
        log(
            f"{input_file.name}: primary conversion failed with error: {exc}. "
            "Retrying with TiffSlideSource."
        )
        WsiDicomizer.convert(
            input_file,
            output_dcm_dir,
            preferred_source=TiffSlideSource,
            metadata=metadata,
            add_missing_levels=True,
            include_confidential=False,
        )

    kept_files = postprocess_dicom_files(output_dcm_dir)

    if not kept_files:
        fail(f"{input_file.name}: conversion produced no non-thumbnail DICOM files.")

    log(f"{input_file.name}: converted to {len(kept_files)} DICOM file(s).")


def main():
    log(f"Input directory: {INPUT_DIR}")
    log(f"Output directory: {OUTPUT_DIR}")

    if not INPUT_DIR.is_dir():
        fail(f"Input directory does not exist: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    input_files = sorted(
        path
        for path in INPUT_DIR.iterdir()
        if path.is_file() and not path.name.startswith(".")
    )

    if not input_files:
        fail(f"No input files found in {INPUT_DIR}")

    log(f"Number of input files found: {len(input_files)}")

    for input_file in input_files:
        convert_wsi_file(input_file)

    log(
        "This conversion was done with wsidicomizer as backbone. "
        "wsidicomizer: Copyright 2021 Sectra AB, licensed under Apache 2.0."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)